#!/usr/bin/env python3
"""
Commande ``build-template`` — construction d'une template via Packer + provisioning.

Pipeline :
1. Ansible/script supprime la template existante dans Proxmox (si vmid utilisé)
2. Packer build crée la VM
3. Connexion SSH ou guest-agent pour provisioning
4. Shutdown propre
5. Suppression des NICs
6. Conversion en template Proxmox

Exemple infra.yaml :
    templates:
      - name: ubuntu
        vmid: 9100
        packer: ubuntu
        provisioning:
          method: ssh
          user: ubuntu
          commands:
            - "sudo apt-get update -y"
            - "sudo apt-get install -y qemu-guest-agent"
"""

import subprocess
import time
from pathlib import Path

from rich.console import Console

from ..config import load_config
from ..proxmox import find_vm_node, vm_exists, wait_for_task
from ._helpers import ask_confirm, make_connection

console = Console()

PACKER_DIR = Path(__file__).parent.parent / "packer"


def _delete_existing_template(proxmox, vmid: int) -> None:
    """Supprime une template existante si elle existe."""

    if not vm_exists(proxmox, vmid):
        return

    node = find_vm_node(proxmox, vmid)
    if node is None:
        return

    console.print(f"  [yellow]Template vmid={vmid} existante → suppression...[/yellow]")
    # Force stop + delete (même si c'est une template)
    try:
        proxmox.nodes(node).qemu(vmid).status.stop.post(forceStop=1)
        time.sleep(2)
    except Exception:
        pass
    try:
        task = proxmox.nodes(node).qemu(vmid).delete(purge=1)
        wait_for_task(proxmox, node, task)
        console.print(f"  [red]✖ Template vmid={vmid} supprimée[/red]")
    except Exception as e:
        console.print(f"  [yellow]⚠  Suppression template vmid={vmid} : {e}[/yellow]")


def _run_packer(tmpl, settings, config, target_node: str) -> bool:
    """Exécute Packer pour construire une template.

    Passe toutes les variables requises via des flags ``-var``.

    Returns:
        True si Packer a réussi.
    """
    packer_dir = PACKER_DIR / tmpl.packer
    if not packer_dir.exists():
        console.print(f"[red]❌ Répertoire Packer introuvable : {packer_dir}[/red]")
        return False

    # Variables Proxmox/infra injectées automatiquement
    packer_vars: dict[str, str] = {
        "proxmox_api_url": f"https://{settings.host}:8006/api2/json",
        "proxmox_api_token_id": settings.token_id,
        "proxmox_api_token_secret": settings.token_secret,
        "proxmox_node": target_node,
        "vm_id": str(tmpl.vmid),
        "vm_name": tmpl.name,
        "storage_pool": config.openwrt.storage,
        "bridge": config.openwrt.wan_bridge,
        "iso_storage_pool": tmpl.iso_storage_pool,
        "custom_user": tmpl.provisioning.user,
    }

    if tmpl.iso_file:
        packer_vars["iso_file"] = tmpl.iso_file

    # Variables supplémentaires définies dans infra.yaml (surcharge)
    packer_vars.update(tmpl.packer_vars)

    cmd = ["packer", "build"]
    for key, value in packer_vars.items():
        cmd += ["-var", f"{key}={value}"]
    cmd.append(".")

    console.print(f"  [cyan]Packer build : {packer_dir}[/cyan]")
    result = subprocess.run(cmd, cwd=packer_dir)
    if result.returncode != 0:
        console.print(f"[red]❌ Packer a échoué (code {result.returncode})[/red]")
        return False
    return True


def _provision_via_ssh(proxmox, node: str, vmid: int, user: str, commands: list[str]) -> None:
    """Exécute les commandes de provisioning via SSH."""
    import paramiko

    # Récupérer l'IP depuis la config de la VM
    from ..proxmox import get_vm_wan_ip as _get_ip

    ip = _get_ip(proxmox, node, vmid)
    if not ip:
        raise RuntimeError(f"Impossible de récupérer l'IP de la VM vmid={vmid}")

    console.print(f"  [cyan]SSH → {user}@{ip}[/cyan]")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Attendre que SSH soit disponible (max 60s)
    for attempt in range(20):
        try:
            client.connect(ip, username=user, timeout=10, look_for_keys=True)
            break
        except Exception:
            if attempt == 19:
                raise RuntimeError(f"SSH indisponible sur {ip} après 60s")
            time.sleep(3)

    try:
        for cmd in commands:
            console.print(f"  [dim]$ {cmd}[/dim]")
            stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                err = stderr.read().decode().strip()
                raise RuntimeError(f"Commande échouée (exit {exit_code}) : {cmd}\n{err}")
    finally:
        client.close()


def _provision_via_guest_agent(proxmox, node: str, vmid: int, commands: list[str]) -> None:
    """Exécute les commandes de provisioning via QEMU guest-agent."""
    for cmd in commands:
        console.print(f"  [dim]$ {cmd}[/dim]")
        parts = cmd.split()
        try:
            proxmox.nodes(node).qemu(vmid).agent.exec.post(
                command=parts[0],
                **{"input-data": " ".join(parts[1:])},
            )
        except Exception as e:
            raise RuntimeError(f"guest-agent exec échoué : {cmd} → {e}")


def _convert_to_template(proxmox, node: str, vmid: int) -> None:
    """Supprime les NICs et convertit la VM en template Proxmox."""
    console.print("  [cyan]Suppression des NICs...[/cyan]")
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()
        nic_keys = [k for k in cfg if k.startswith("net")]
        if nic_keys:
            delete_param = ",".join(nic_keys)
            proxmox.nodes(node).qemu(vmid).config.put(delete=delete_param)
    except Exception as e:
        console.print(f"  [yellow]⚠  Suppression NICs : {e}[/yellow]")

    console.print("  [cyan]Conversion en template...[/cyan]")
    proxmox.nodes(node).qemu(vmid).template.post()
    console.print(f"  [green]✓ vmid={vmid} converti en template[/green]")


def cmd_build_template(args) -> None:
    """Construit une template via Packer + provisioning."""
    config = load_config()
    proxmox = make_connection()

    template_name = getattr(args, "name", None)

    # Sélectionner la (les) template(s) à construire
    if template_name:
        templates = [t for t in config.templates if t.name == template_name]
        if not templates:
            console.print(f"[red]❌ Template '{template_name}' introuvable dans infra.yaml[/red]")
            return
    else:
        templates = config.templates
        if not templates:
            console.print(
                "[dim]Aucune template définie dans infra.yaml (section 'templates:').[/dim]"
            )
            return

    from ..config import load_proxmox_settings
    from ..proxmox import pick_node

    settings = load_proxmox_settings()

    for tmpl in templates:
        console.print(f"\n[bold cyan]═══ Template : {tmpl.name} (vmid={tmpl.vmid}) ═══[/bold cyan]")

        if not getattr(args, "yes", False):
            if not ask_confirm(f"Construire la template '{tmpl.name}' (vmid={tmpl.vmid}) ?"):
                console.print("[dim]Ignoré.[/dim]")
                continue

        # Nœud cible : explicite dans infra.yaml ou le moins chargé
        target_node = tmpl.node or pick_node(proxmox)

        # Étape 1 : supprimer la template existante
        _delete_existing_template(proxmox, tmpl.vmid)

        # Étape 2 : Packer build (si configuré)
        if tmpl.packer:
            if not _run_packer(tmpl, settings, config, target_node):
                console.print(f"[red]❌ Build Packer échoué pour '{tmpl.name}'[/red]")
                continue

        # Attendre que la VM soit créée et démarrée
        node = None
        for _ in range(30):
            node = find_vm_node(proxmox, tmpl.vmid)
            if node:
                break
            time.sleep(3)

        if node is None:
            console.print(f"[red]❌ VM vmid={tmpl.vmid} introuvable après build Packer[/red]")
            continue

        # Étape 3 : Provisioning
        prov = tmpl.provisioning
        if prov.commands:
            console.print(f"  [cyan]Provisioning ({prov.method})...[/cyan]")
            try:
                if prov.method == "ssh":
                    _provision_via_ssh(proxmox, node, tmpl.vmid, prov.user, prov.commands)
                elif prov.method == "guest-agent":
                    _provision_via_guest_agent(proxmox, node, tmpl.vmid, prov.commands)
                console.print("  [green]✓ Provisioning terminé[/green]")
            except Exception as e:
                console.print(f"  [red]❌ Provisioning échoué : {e}[/red]")
                continue

        # Étape 4 : Shutdown propre
        console.print("  [cyan]Shutdown...[/cyan]")
        try:
            task = proxmox.nodes(node).qemu(tmpl.vmid).status.shutdown.post()
            wait_for_task(proxmox, node, task, timeout=120)
        except Exception as e:
            console.print(f"  [yellow]⚠  Shutdown : {e} — forçage...[/yellow]")
            try:
                proxmox.nodes(node).qemu(tmpl.vmid).status.stop.post()
                time.sleep(5)
            except Exception:
                pass

        # Étape 5 : Conversion en template
        _convert_to_template(proxmox, node, tmpl.vmid)

        console.print(
            f"\n[bold green]✓ Template '{tmpl.name}' construite avec succès (vmid={tmpl.vmid})[/bold green]"
        )

#!/usr/bin/env python3
"""
Commande ``build-template`` — construction d'une template cloud-init via l'API Proxmox.

Pipeline pour chaque template :
1. Suppression de la template existante (si vmid déjà utilisé)
2. Suppression de l'image existante sur le stockage (si déjà téléchargée)
3. Téléchargement de l'image cloud depuis iso_url via l'API Proxmox
4. Création de la VM avec import-from + cloud-init
5. Redimensionnement du disque
6. Démarrage de la VM + attente du guest agent (pré-installé dans les images cloud)
7. Shutdown propre
8. Nettoyage de l'image téléchargée
9. Conversion en template Proxmox

Note : les images cloud Ubuntu/Fedora/Debian incluent qemu-guest-agent nativement.
       Aucun provisioning SSH ni snippet cloud-init n'est nécessaire.

Exemple infra.yaml :
    templates:
      - name: ubuntu-24.04
        vmid: 9100
        iso_url: "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img"
        storage_pool: local-lvm
        iso_storage_pool: local
        bridge: vmbr0
        cloud_init_user: ubuntu
        memory: 2048
        cores: 2
        disk_size: "20G"
"""

import subprocess
import time

from rich.console import Console

from ..config import load_config
from ..proxmox import add_vm_to_pool, find_vm_node, pick_node, vm_exists, wait_for_task
from ._helpers import ask_confirm, make_connection

console = Console()

_DISK_IMAGE_EXTENSIONS = {".img", ".qcow2", ".vmdk", ".raw", ".vhd", ".vhdx"}


# ── Helpers bas niveau ────────────────────────────────────────────────────────


def _iso_filename_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _is_disk_image(filename: str) -> bool:
    from pathlib import Path

    return Path(filename).suffix.lower() in _DISK_IMAGE_EXTENSIONS


def _image_content_type(filename: str) -> str:
    return "import" if _is_disk_image(filename) else "iso"


def _image_volid(storage: str, filename: str) -> str:
    if _is_disk_image(filename):
        return f"{storage}:import/{filename}"
    return f"{storage}:iso/{filename}"


# ── Helpers pool ──────────────────────────────────────────────────────────────


def _ensure_template_pool(proxmox, pool_name: str) -> None:
    """Crée le pool template s'il n'existe pas encore."""
    try:
        proxmox.pools(pool_name).get()
    except Exception:
        proxmox.pools.post(poolid=pool_name)
        console.print(f"[green]✓ Pool '{pool_name}' créé[/green]")


# ── Helpers virt-customize ─────────────────────────────────────────────────────


def _get_storage_base_path(proxmox, storage: str) -> str:
    """Retourne le chemin de base du stockage (vide si non directory)."""
    try:
        for s in proxmox.storage.get():
            if s.get("storage") == storage:
                return str(s.get("path", ""))
    except Exception:
        pass
    return ""


def _find_image_path(node: str, storage_path: str, filename: str) -> str:
    """Localise le fichier image sur le nœud via SSH (find récursif)."""
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{node}",
            f"find '{storage_path}' -name '{filename}' 2>/dev/null | head -1",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _virt_customize_image(node: str, image_path: str, packages: list[str]) -> None:
    """Pré-installe des packages dans l'image via virt-customize (SSH root@node).

    Prérequis : libguestfs-tools installé sur le nœud Proxmox.
    """
    pkg_str = ",".join(packages)
    # Active le service qemu-guest-agent : systemd (Ubuntu/Debian/Fedora) ou OpenRC (Alpine)
    # rc-update ne fonctionne pas dans un chroot guestfs — on crée le symlink runlevel directement
    enable_ga = (
        "systemctl enable qemu-guest-agent.service 2>/dev/null"
        "; ln -sf /etc/init.d/qemu-guest-agent /etc/runlevels/default/qemu-guest-agent 2>/dev/null"
        "; true"
    )
    remote_cmd = (
        "command -v virt-customize >/dev/null 2>&1"
        " || apt-get install -y -q libguestfs-tools >&2"
        f" && virt-customize -a '{image_path}'"
        f" --install {pkg_str}"
        f" --run-command '{enable_ga}'"
        " --run-command 'sed -i \"/reset_rmc/d\" /etc/cloud/cloud.cfg 2>/dev/null; true'"
        " --run-command ': > /etc/machine-id'"
    )
    result = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", f"root@{node}", remote_cmd],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"virt-customize failed:\n{result.stderr.strip()}")


# ── Étapes du pipeline ────────────────────────────────────────────────────────


def _delete_existing_template(proxmox, vmid: int) -> None:
    if not vm_exists(proxmox, vmid):
        return
    node = find_vm_node(proxmox, vmid)
    if node is None:
        return
    console.print(f"  [yellow]Template vmid={vmid} existante → suppression...[/yellow]")
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


def _delete_existing_iso(proxmox, node: str, storage: str, filename: str) -> None:
    volid = _image_volid(storage, filename)
    try:
        contents = proxmox.nodes(node).storage(storage).content.get()
        if any(c.get("volid") == volid for c in contents):
            proxmox.nodes(node).storage(storage).content(volid).delete()
            console.print(f"  [yellow]↻ Image supprimée : {volid}[/yellow]")
    except Exception as e:
        console.print(f"  [yellow]⚠  Suppression image {volid} : {e}[/yellow]")


def _download_image(proxmox, node: str, storage: str, url: str, filename: str) -> str:
    """Télécharge l'image sur le stockage Proxmox via l'API. Retourne le volid."""
    console.print(f"  [cyan]Téléchargement : {url}[/cyan]")
    task = (
        proxmox.nodes(node)
        .storage(storage)("download-url")
        .post(
            content=_image_content_type(filename),
            filename=filename,
            url=url,
        )
    )
    wait_for_task(
        proxmox,
        node,
        task,
        timeout=600,
        poll_interval=5,
        progress_label="Téléchargement",
    )
    volid = _image_volid(storage, filename)
    console.print(f"  [green]✓ Image téléchargée : {volid}[/green]")
    return volid


def _create_vm(
    proxmox, node: str, tmpl, iso_volid: str, eff_user: str = "", eff_pass: str = ""
) -> None:
    """Crée la VM avec import-from.

    Si tmpl.cloudinit=True  : drive cloud-init + agent + ciuser + ipconfig0 (défaut).
    Si tmpl.cloudinit=False : VM nue sans cloud-init ni agent (ex: OPNsense, pfSense).
    """
    kwargs: dict = dict(
        vmid=tmpl.vmid,
        name=tmpl.name,
        memory=tmpl.memory,
        cores=tmpl.cores,
        sockets=1,
        cpu=tmpl.cpu_type,
        net0=f"virtio,bridge={tmpl.bridge}",
        virtio0=f"{tmpl.storage_pool}:0,import-from={iso_volid}",
        boot="order=virtio0",
        serial0="socket",
        vga="serial0",
        ostype=tmpl.ostype,
    )
    if tmpl.cloudinit:
        kwargs["ide2"] = f"{tmpl.storage_pool}:cloudinit"
        kwargs["agent"] = "enabled=1"
        kwargs["ciuser"] = eff_user
        kwargs["cipassword"] = eff_pass
        kwargs["ipconfig0"] = "ip=dhcp"

    task = proxmox.nodes(node).qemu.post(**kwargs)
    if task:
        wait_for_task(
            proxmox,
            node,
            task,
            timeout=120,
            progress_label="Import disque",
        )
    console.print(f"  [green]✓ VM vmid={tmpl.vmid} créée[/green]")


def _resize_disk(proxmox, node: str, tmpl) -> None:
    try:
        proxmox.nodes(node).qemu(tmpl.vmid).resize.put(disk="virtio0", size=tmpl.disk_size)
        console.print(f"  [green]✓ Disque → {tmpl.disk_size}[/green]")
    except Exception as e:
        console.print(f"  [yellow]⚠  Resize disque : {e}[/yellow]")


def _start_vm(proxmox, node: str, vmid: int) -> None:
    task = proxmox.nodes(node).qemu(vmid).status.start.post()
    if task:
        wait_for_task(proxmox, node, task, timeout=60)
    console.print(f"  [green]✓ VM vmid={vmid} démarrée[/green]")


def _wait_for_guest_agent(proxmox, node: str, vmid: int, timeout: int = 300) -> bool:
    """Attend que le guest agent soit disponible (VM bootée + cloud-init terminé)."""
    import sys

    console.print("  [cyan]Attente du guest agent...[/cyan]")
    start = time.time()
    deadline = start + timeout
    while time.time() < deadline:
        try:
            proxmox.nodes(node).qemu(vmid).agent("get-osinfo").get()
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()
            return True
        except Exception:
            elapsed = int(time.time() - start)
            sys.stderr.write(f"\r  ⏳ guest agent [{elapsed}s / {timeout}s]")
            sys.stderr.flush()
            time.sleep(10)
    sys.stderr.write("\r\033[K")
    sys.stderr.flush()
    return False


def _wait_vm_stopped(proxmox, node: str, vmid: int, timeout: int = 60) -> bool:
    """Attend que la VM soit à l'état 'stopped'."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = proxmox.nodes(node).qemu(vmid).status.current.get()
            if status.get("status") == "stopped":
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def _wait_vm_unlocked(proxmox, node: str, vmid: int, timeout: int = 30) -> None:
    """Attend que le verrou Proxmox de la VM se libère (après un shutdown échoué)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = proxmox.nodes(node).qemu(vmid).status.current.get()
            if not status.get("lock"):
                return
        except Exception:
            return
        time.sleep(2)


def _force_stop_vm(proxmox, node: str, vmid: int) -> None:
    """Force l'arrêt immédiat via l'API Proxmox.

    Attend d'abord que le verrou soit libéré (un shutdown échoué laisse la VM verrouillée).
    """
    _wait_vm_unlocked(proxmox, node, vmid)
    try:
        task = proxmox.nodes(node).qemu(vmid).status.stop.post(forceStop=1)
        if task:
            wait_for_task(proxmox, node, task, timeout=30)
    except Exception as e:
        console.print(f"  [yellow]⚠  Force stop API : {e}[/yellow]")
    _wait_vm_stopped(proxmox, node, vmid, timeout=10)


def _shutdown_vm(proxmox, node: str, vmid: int) -> None:
    console.print("  [cyan]Shutdown...[/cyan]")
    try:
        task = proxmox.nodes(node).qemu(vmid).status.shutdown.post()
        wait_for_task(proxmox, node, task, timeout=120)
    except Exception as e:
        console.print(f"  [yellow]⚠  Shutdown propre : {e} — forçage...[/yellow]")
        _force_stop_vm(proxmox, node, vmid)
        return
    _wait_vm_stopped(proxmox, node, vmid, timeout=10)


def _convert_to_template(
    proxmox,
    node: str,
    vmid: int,
    default_user: str = "",
    default_pass: str = "",
    cloudinit: bool = True,
) -> None:
    """Nettoie la config de build, pousse les defaults cloud-init, convertit en template.

    - Supprime les NICs et ipconfig0 (pas d'IP figée dans la template)
    - Conserve le drive cloud-init (ide2) avec ciuser/cipassword pré-remplis
      → visibles dans l'onglet Cloud-Init lors de la création d'un clone
    """
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()
        to_delete = [k for k in cfg if k.startswith("net")]
        for field in ("ipconfig0", "nameserver", "searchdomain"):
            if field in cfg:
                to_delete.append(field)
        update: dict = {}
        if cloudinit:
            if default_user:
                update["ciuser"] = default_user
            if default_pass:
                update["cipassword"] = default_pass
        else:
            # Pas de cloud-init — supprimer tous les champs ci* s'ils existent
            for field in ("ciuser", "cipassword", "cicustom"):
                if field in cfg:
                    to_delete.append(field)
        if to_delete:
            proxmox.nodes(node).qemu(vmid).config.put(delete=",".join(to_delete))
        if update:
            proxmox.nodes(node).qemu(vmid).config.put(**update)
    except Exception as e:
        console.print(f"  [yellow]⚠  Nettoyage config : {e}[/yellow]")
    proxmox.nodes(node).qemu(vmid).template.post()
    console.print(f"  [green]✓ vmid={vmid} converti en template (cloud-init prêt)[/green]")


# ── Commande principale ───────────────────────────────────────────────────────


def cmd_build_template(args) -> None:
    """Construit une ou plusieurs templates cloud-init via l'API Proxmox."""
    config = load_config()
    proxmox = make_connection()

    tmpl_cfg = config.templates

    # Sélection des templates : * ou nom1,nom2 ou rien (= tout)
    names_arg: str | None = getattr(args, "names", None)
    if not names_arg or names_arg == "*":
        templates = tmpl_cfg.sources
    else:
        requested = {n.strip() for n in names_arg.split(",")}
        templates = [t for t in tmpl_cfg.sources if t.name in requested]
        unknown = requested - {t.name for t in templates}
        if unknown:
            console.print(
                f"[red]❌ Templates introuvables dans infra.yaml : {', '.join(sorted(unknown))}[/red]"
            )
            return

    if not templates:
        console.print(
            "[dim]Aucune template définie dans infra.yaml (section 'templates.sources:').[/dim]"
        )
        return

    pool_name = config.openwrt.template_pool
    _ensure_template_pool(proxmox, pool_name)

    for tmpl in templates:
        # Résolution user/pass : surcharge par template > défaut global
        eff_user = tmpl.cloud_init_user or tmpl_cfg.default_user
        eff_pass = tmpl.cloud_init_password or tmpl_cfg.default_pass

        console.print(f"\n[bold cyan]═══ Template : {tmpl.name} (vmid={tmpl.vmid}) ═══[/bold cyan]")
        if tmpl.cloudinit:
            console.print(f"  [dim]cloud-init user : {eff_user}[/dim]")

        if not getattr(args, "yes", False):
            if not ask_confirm(f"Construire la template '{tmpl.name}' (vmid={tmpl.vmid}) ?"):
                console.print("[dim]Ignoré.[/dim]")
                continue

        node = tmpl.node or pick_node(proxmox)
        filename = tmpl.iso_filename or _iso_filename_from_url(tmpl.iso_url)

        # 1. Supprimer template existante
        _delete_existing_template(proxmox, tmpl.vmid)

        # 2. Supprimer image existante
        _delete_existing_iso(proxmox, node, tmpl.iso_storage_pool, filename)

        # 3. Télécharger l'image
        try:
            iso_volid = _download_image(
                proxmox, node, tmpl.iso_storage_pool, tmpl.iso_url, filename
            )
        except Exception as e:
            console.print(f"[red]❌ Téléchargement échoué : {e}[/red]")
            continue

        # 3b. virt-customize (default_packages + extra_packages, sauf download_packages=False)
        effective_packages = tmpl_cfg.default_packages + tmpl.extra_packages
        if tmpl.download_packages and effective_packages:
            storage_path = _get_storage_base_path(proxmox, tmpl.iso_storage_pool)
            if not storage_path:
                console.print(
                    f"  [yellow]⚠  packages ignorés : chemin du stockage '{tmpl.iso_storage_pool}' introuvable[/yellow]"
                )
            else:
                image_path = _find_image_path(node, storage_path, filename)
                if not image_path:
                    console.print(
                        f"  [yellow]⚠  packages ignorés : fichier '{filename}' introuvable dans {storage_path}[/yellow]"
                    )
                else:
                    console.print(
                        f"  [cyan]virt-customize : {', '.join(effective_packages)}[/cyan]"
                    )
                    try:
                        _virt_customize_image(node, image_path, effective_packages)
                        console.print("  [green]✓ virt-customize terminé[/green]")
                    except Exception as e:
                        console.print(f"[red]❌ virt-customize échoué : {e}[/red]")
                        continue

        # 4. Créer la VM
        try:
            _create_vm(proxmox, node, tmpl, iso_volid, eff_user=eff_user, eff_pass=eff_pass)
        except Exception as e:
            console.print(f"[red]❌ Création VM échouée : {e}[/red]")
            continue

        # 5. Redimensionner le disque
        _resize_disk(proxmox, node, tmpl)

        if tmpl.cloudinit:
            # 6. Démarrer + attendre le guest agent (cloud-init inclus dans l'image)
            try:
                _start_vm(proxmox, node, tmpl.vmid)
            except Exception as e:
                console.print(f"[red]❌ Démarrage VM : {e}[/red]")
                continue

            if not _wait_for_guest_agent(proxmox, node, tmpl.vmid, timeout=tmpl.boot_timeout):
                # Premier boot parfois bloqué (ex: Alpine/OpenRC) — reset et nouvel essai
                console.print(
                    "  [yellow]⚠  Timeout guest agent — reset VM et nouvel essai...[/yellow]"
                )
                try:
                    task = proxmox.nodes(node).qemu(tmpl.vmid).status.reset.post()
                    if task:
                        wait_for_task(proxmox, node, task, timeout=30)
                except Exception as e:
                    console.print(f"  [yellow]⚠  Reset : {e}[/yellow]")
                if not _wait_for_guest_agent(
                    proxmox, node, tmpl.vmid, timeout=tmpl.boot_timeout // 2
                ):
                    console.print(
                        "[red]❌ Timeout guest agent — vérifier que l'image inclut qemu-guest-agent[/red]"
                    )
                    continue

            console.print("  [green]✓ Guest agent disponible[/green]")

            # 7. Shutdown
            _shutdown_vm(proxmox, node, tmpl.vmid)
        else:
            console.print("  [dim]cloud-init désactivé — pas de boot[/dim]")

        # 8. Nettoyage image
        _delete_existing_iso(proxmox, node, tmpl.iso_storage_pool, filename)

        # 9. Conversion en template (retry 3x si VM encore en cours d'arrêt)
        converted = False
        for attempt in range(3):
            try:
                _convert_to_template(
                    proxmox,
                    node,
                    tmpl.vmid,
                    default_user=eff_user,
                    default_pass=eff_pass,
                    cloudinit=tmpl.cloudinit,
                )
                converted = True
                break
            except Exception as e:
                if "running" in str(e).lower() and attempt < 2:
                    console.print(
                        f"  [yellow]⚠  VM encore active, force stop (essai {attempt + 1}/3)...[/yellow]"
                    )
                    _force_stop_vm(proxmox, node, tmpl.vmid)
                else:
                    console.print(f"[red]❌ Conversion en template : {e}[/red]")
                    break
        if not converted:
            continue

        # 10. Ajout au pool template
        try:
            add_vm_to_pool(proxmox, pool_name, tmpl.vmid)
            console.print(f"  [green]✓ Ajoutée au pool '{pool_name}'[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠  Ajout au pool : {e}[/yellow]")

        console.print(
            f"\n[bold green]✓ Template '{tmpl.name}' construite avec succès (vmid={tmpl.vmid})[/bold green]"
        )

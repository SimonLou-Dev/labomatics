#!/usr/bin/env python3
"""
Commande ``setup`` — assistant d'installation interactif labomatics.

Étapes :
1. Déjà initialisé ?  → skip les étapes 2-3
2. Saisie interactive des credentials Proxmox → écriture .env
3. Copie des templates (infra.yaml, students.csv)
4. Vérification de la connexion Proxmox
5. Vérification du stockage partagé (multi-nœuds)
6. Ouverture de infra.yaml dans vim/nano pour édition
7. Vérifications post-édition (bridges, storages, zone SDN)
8. Création du pool template
9. Conseil SPICE
10. Proposition de construire la template OpenWrt
"""

import getpass
import os
import shutil
import subprocess
import time
from pathlib import Path

from rich.console import Console

console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
CONFIG_DIR = Path("/etc/labomatics")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ask(prompt: str, default: str = "") -> str:
    """Saisie interactive avec valeur par défaut."""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"   {prompt}{suffix} : ").strip()
        return val or default
    except (EOFError, KeyboardInterrupt):
        return default


def _confirm(message: str) -> bool:
    """Confirmation interactive y/N."""
    try:
        return input(f"\n{message} [y/N] ").strip().lower() in ("y", "yes", "o", "oui")
    except (EOFError, KeyboardInterrupt):
        return False


def _open_editor(file_path: Path) -> None:
    """Ouvre le fichier dans l'éditeur disponible ($VISUAL/$EDITOR, vim, nano)."""
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        for candidate in ("vim", "nano", "vi"):
            if shutil.which(candidate):
                editor = candidate
                break

    if editor:
        console.print(
            f"  [dim]Ouverture dans {editor} — sauvegardez et quittez pour continuer[/dim]"
        )
        try:
            subprocess.run([editor, str(file_path)])
        except Exception as e:
            console.print(f"  [yellow]⚠  Impossible d'ouvrir l'éditeur : {e}[/yellow]")
            console.print(f"  Éditez manuellement : [cyan]{file_path}[/cyan]")
            input("  Appuyez sur Entrée une fois terminé...")
    else:
        console.print(f"  [yellow]Aucun éditeur trouvé. Éditez : [cyan]{file_path}[/cyan][/yellow]")
        input("  Appuyez sur Entrée une fois terminé...")


def _check_shared_storage(proxmox, nodes: list) -> None:
    """Vérifie la présence d'un stockage partagé entre tous les nœuds."""
    SHARED_TYPES = {"rbd", "nfs", "nfs4", "glusterfs", "cephfs", "zfs", "pbs", "cifs"}
    per_node: dict[str, dict] = {}
    for n in nodes:
        storages = proxmox.nodes(n["node"]).storage.get()
        per_node[n["node"]] = {s["storage"]: s for s in storages}

    all_names = set.intersection(*[set(d.keys()) for d in per_node.values()])
    shared = [
        name
        for name in all_names
        if any(per_node[n["node"]][name].get("type") in SHARED_TYPES for n in nodes)
    ]

    if shared:
        console.print(
            f"  [green]✓ Stockages partagés détectés : {', '.join(sorted(shared))}[/green]"
        )
    else:
        console.print(
            "  [yellow]⚠  Aucun stockage partagé détecté entre les nœuds.[/yellow]\n"
            "     Pour les clones cross-node, configurez Ceph, NFS ou ZFS partagé.\n"
            "     Consultez : docs/admin/setup.md"
        )


def _verify_config(proxmox, config, nodes: list) -> bool:
    """Vérifie bridges, storages et zone SDN après édition de infra.yaml.

    Retourne True si tout est OK, False si des avertissements bloquants subsistent.
    """
    from ..proxmox import check_sdn_zone_exists

    storage = config.openwrt.storage
    wan_bridge = config.openwrt.wan_bridge
    zone = config.openwrt.network.zone_name
    ok = True

    for n in nodes:
        node_name = n["node"]

        # Storage
        try:
            storages = [s["storage"] for s in proxmox.nodes(node_name).storage.get()]
            if storage in storages:
                console.print(f"  [green]✓ Storage '{storage}' — {node_name}[/green]")
            else:
                console.print(
                    f"  [red]✗  Storage '{storage}' absent sur {node_name}[/red]\n"
                    f"     Storages disponibles : {', '.join(storages)}"
                )
                ok = False
        except Exception as e:
            console.print(
                f"  [yellow]⚠  Impossible de vérifier le storage sur {node_name} : {e}[/yellow]"
            )

        # Bridge WAN
        try:
            networks = proxmox.nodes(node_name).network.get()
            bridges = [net["iface"] for net in networks if net.get("type") == "bridge"]
            if wan_bridge in bridges:
                console.print(f"  [green]✓ Bridge '{wan_bridge}' — {node_name}[/green]")
            else:
                console.print(
                    f"  [red]✗  Bridge '{wan_bridge}' absent sur {node_name}[/red]\n"
                    f"     Bridges disponibles : {', '.join(bridges)}"
                )
                ok = False
        except Exception as e:
            console.print(
                f"  [yellow]⚠  Impossible de vérifier les bridges sur {node_name} : {e}[/yellow]"
            )

    # Zone SDN
    try:
        if check_sdn_zone_exists(proxmox, zone):
            console.print(f"  [green]✓ Zone SDN '{zone}' présente[/green]")
        else:
            console.print(
                f"  [red]✗  Zone SDN '{zone}' absente[/red]\n"
                "     Créez-la dans Proxmox → Datacenter → SDN → Zones (type VXLAN)"
            )
            ok = False
    except Exception as e:
        console.print(f"  [yellow]⚠  Vérification SDN : {e}[/yellow]")

    return ok


# ── Commande principale ───────────────────────────────────────────────────────


def cmd_setup(args) -> None:
    """Assistant d'installation interactif labomatics."""
    target_dir = getattr(args, "dir", None)
    config_dir = Path(target_dir) if target_dir else CONFIG_DIR
    env_file = config_dir / ".env"
    infra_file = config_dir / "infra.yaml"
    csv_file = config_dir / "students.csv"

    console.print("\n[bold cyan]╔══════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║    labomatics — setup        ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════╝[/bold cyan]\n")

    # ── Étapes 1-2 : création des fichiers manquants uniquement ──────────────

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        console.print(
            f"[red]❌ Permission refusée pour créer {config_dir}[/red]\n"
            f"  Essayez : [bold]sudo labomatics setup[/bold]\n"
            f"  Ou : [bold]labomatics setup --dir ./config[/bold]"
        )
        return

    # Étape 1 : credentials Proxmox (.env)
    if not env_file.exists():
        console.print("[bold]Étape 1/9 — Credentials Proxmox[/bold]")
        console.print("  Créez un API token dans Proxmox :")
        console.print("    Datacenter → Permissions → API Tokens → Add")
        console.print(
            "    ⚠  Décochez [bold]Privilege Separation[/bold] pour que le token hérite des droits de l'utilisateur\n"
        )

        host = _ask("PROXMOX_HOST        (IP ou hostname)")
        token_id = _ask("PROXMOX_TOKEN_ID    (user@realm!token-name)")
        token_secret = getpass.getpass("   PROXMOX_TOKEN_SECRET                  : ")

        env_file.write_text(
            f'PROXMOX_HOST="{host}"\n'
            f'PROXMOX_TOKEN_ID="{token_id}"\n'
            f'PROXMOX_TOKEN_SECRET="{token_secret}"\n'
        )
        console.print("  [green]✓ .env créé[/green]\n")
    else:
        console.print("[bold]Étape 1/9 — Credentials Proxmox[/bold]")
        console.print("  [dim]⏭  .env déjà présent — ignoré[/dim]\n")

    # Étape 2 : fichiers de configuration (infra.yaml, students.csv)
    console.print("[bold]Étape 2/9 — Création des fichiers de configuration[/bold]")
    for src_name, dst in [
        ("infra.yaml.example", infra_file),
        ("students.csv.example", csv_file),
    ]:
        src = TEMPLATES_DIR / src_name
        if not dst.exists() and src.exists():
            shutil.copy(src, dst)
            console.print(f"  [green]✓ {dst.name} créé[/green]")
        elif dst.exists():
            console.print(f"  [dim]⏭  {dst.name} déjà présent — ignoré[/dim]")
    console.print()

    # ── Étape 3 : connexion Proxmox ───────────────────────────────────────────

    console.print("[bold]Étape 3/9 — Vérification de la connexion Proxmox[/bold]")
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file)
        from ..config import load_proxmox_settings
        from ..proxmox import connect

        settings = load_proxmox_settings()
        proxmox = connect(settings)
        nodes = proxmox.nodes.get()
        online = [n for n in nodes if n.get("status") == "online"]

        console.print(f"  [green]✓ Connecté — {len(online)} nœud(s) en ligne[/green]")
        for n in sorted(online, key=lambda x: x["node"]):
            mem_gb = n.get("maxmem", 0) // (1024**3)
            cpu = n.get("maxcpu", "?")
            console.print(f"    · {n['node']}  {cpu} vCPU  {mem_gb} GB RAM")
        console.print()
    except Exception as e:
        console.print(f"  [red]❌ Connexion échouée : {e}[/red]")
        console.print(f"  Vérifiez [cyan]{env_file}[/cyan] et réessayez.")
        return

    # ── Étape 4 : stockage partagé (multi-nœuds) ──────────────────────────────

    if len(online) > 1:
        console.print("[bold]Étape 4/9 — Stockage partagé (cluster multi-nœuds détecté)[/bold]")
        _check_shared_storage(proxmox, online)
    else:
        console.print("[bold]Étape 4/9 — Stockage (nœud unique)[/bold]")
        node_name = online[0]["node"]
        try:
            storages = [s["storage"] for s in proxmox.nodes(node_name).storage.get()]
            console.print(
                f"  Stockages disponibles sur [cyan]{node_name}[/cyan] : {', '.join(storages)}"
            )
        except Exception as e:
            console.print(f"  [yellow]⚠  Impossible de lister les stockages : {e}[/yellow]")
    console.print()

    # ── Étape 5 : édition infra.yaml ──────────────────────────────────────────

    console.print("[bold]Étape 5/9 — Configuration de infra.yaml[/bold]")
    console.print(f"  Fichier : [cyan]{infra_file}[/cyan]")
    console.print("  [dim]Ouverture dans 2 secondes...[/dim]")
    time.sleep(2)
    _open_editor(infra_file)
    console.print()

    # ── Étape 6 : vérifications post-édition (retry toutes les 10s) ──────────

    console.print("[bold]Étape 6/9 — Vérifications post-configuration[/bold]")
    from ..config import InfraConfig, load_config

    config: InfraConfig | None = None
    while True:
        try:
            config = load_config()
            ok = _verify_config(proxmox, config, online)
        except Exception as e:
            console.print(f"  [red]❌ {e}[/red]")
            ok = False

        if ok:
            break

        console.print(
            f"\n  Corrigez [cyan]{infra_file}[/cyan] — nouvelle vérification dans 10 s  "
            "(Ctrl+C pour annuler)"
        )
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            console.print("\n[yellow]Setup annulé.[/yellow]")
            return
        console.print("\n[bold]Étape 6/9 — Vérifications post-configuration[/bold]")
    assert config is not None
    console.print()

    # ── Étape 7 : pool template ───────────────────────────────────────────────

    console.print("[bold]Étape 7/9 — Pool template[/bold]")
    pool_name = config.openwrt.template_pool
    try:
        proxmox.pools(pool_name).get()
        console.print(f"  [dim]⏭  Pool '{pool_name}' déjà présent[/dim]")
    except Exception:
        try:
            proxmox.pools.post(poolid=pool_name)
            console.print(f"  [green]✓ Pool '{pool_name}' créé[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠  Création pool : {e}[/yellow]")
    console.print()

    # ── Étape 8 : conseil SPICE ───────────────────────────────────────────────

    console.print("[bold]Étape 8/9 — Conseil SPICE[/bold]")
    console.print(
        "  Les templates cloud-init utilisent [bold]serial0: socket[/bold] comme console.\n"
        "  Sans SPICE, l'interface Proxmox peut mélanger les sorties serial des VMs.\n\n"
        "  Installez un viewer SPICE sur vos postes admin :\n"
        "    · Linux   : [cyan]apt install virt-viewer[/cyan]\n"
        "    · macOS   : [cyan]brew install virt-viewer[/cyan]\n"
        "    · Windows : https://virt-manager.org/download/\n\n"
        "  Dans Proxmox, activez SPICE sur chaque VM :\n"
        "    VM → Hardware → Display → [bold]SPICE[/bold]\n"
    )

    # ── Étape 9 : template OpenWrt ────────────────────────────────────────────

    console.print("[bold]Étape 9/9 — Template OpenWrt[/bold]")
    if _confirm("  Construire la template OpenWrt maintenant ?"):
        from .build_openwrt import cmd_build_openwrt

        _tpl_pool = config.openwrt.template_pool  # type: ignore[union-attr]

        class _Args:
            version = None
            vmid = None
            storage = None
            password = "openwrt"
            template_pool = _tpl_pool
            yes = True

        try:
            cmd_build_openwrt(_Args())
        except Exception as e:
            console.print(f"  [red]❌ Build OpenWrt : {e}[/red]")
    else:
        console.print(
            "  [dim]Ignoré. Lancez plus tard : [bold]labomatics template openwrt[/bold][/dim]"
        )

    # ── Résumé ────────────────────────────────────────────────────────────────

    console.print("\n[bold green]✓ Setup terminé ![/bold green]\n")
    console.print("  Étapes suivantes :\n")
    console.print(f"    1. Remplir  [cyan]{csv_file}[/cyan]")
    console.print("    2. Vérifier [bold]labomatics student diff[/bold]")
    console.print("    3. Appliquer [bold]labomatics student apply[/bold]\n")

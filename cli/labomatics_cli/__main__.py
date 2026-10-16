#!/usr/bin/env python3
"""CLI labomatics v0.4 - Orchestration centrale."""

import argparse
import sys
import warnings

from rich.console import Console

from .commands.templates import cmd_templates
from .commands.templates.build_openwrt import DEFAULT_VMID, run_build
from .installer.app import InstallerApp

# Suppress SSL warnings for self-signed certs (Proxmox, etc)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

console = Console()


def cmd_install(args: argparse.Namespace) -> int:
    """Lance le wizard d'installation.

    Args:
        args: Arguments de la ligne de commande (`cluster`).

    Returns:
        0 si le wizard est allé au bout, 1 s'il a été abandonné.
    """
    return InstallerApp(cluster=args.cluster).run()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="labomatics",
        description="labomatics v0.4 — Orchestration centrale pour Proxmox",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # install command
    install_parser = subparsers.add_parser(
        "install",
        help="Initialiser le cluster central",
    )
    tempaltes_parser = subparsers.add_parser(
        "template",
        help="Gestion des templates",
    )
    install_parser.add_argument(
        "--cluster",
        help="Nom du cluster à installer, reprendre ou modifier",
    )
    install_parser.set_defaults(func=cmd_install)
    tempaltes_parser.set_defaults(func=cmd_templates)

    template_subparsers = tempaltes_parser.add_subparsers(dest="template_action")
    build_openwrt_parser = template_subparsers.add_parser(
        "build-openwrt",
        help=(
            "Builder la template OpenWrt à distance sur un cluster choisi "
            "(aucun accès local au nœud Proxmox requis, seulement SSH root)"
        ),
    )
    build_openwrt_parser.add_argument(
        "--cluster", help="Nom d'un cluster déjà configuré par `labomatics install`"
    )
    build_openwrt_parser.add_argument(
        "--cluster-url", help="URL Proxmox (ex: https://10.0.0.1:8006)"
    )
    build_openwrt_parser.add_argument("--user", help="User Proxmox (ex: root@pam)")
    build_openwrt_parser.add_argument("--token-id", help="Token ID API Proxmox")
    build_openwrt_parser.add_argument("--token-secret", help="Token secret API Proxmox")
    build_openwrt_parser.add_argument(
        "--node", help="Nœud Proxmox cible (sinon sélection interactive)"
    )
    build_openwrt_parser.add_argument(
        "--ssh-host", help="Hôte/IP SSH du nœud cible (sinon résolu via l'API)"
    )
    build_openwrt_parser.add_argument(
        "--storage", help="Storage de destination (défaut: local)"
    )
    build_openwrt_parser.add_argument(
        "--version", help="Version OpenWrt (défaut: dernière stable)"
    )
    build_openwrt_parser.add_argument(
        "--vmid", type=int, help=f"VMID de la template (défaut: {DEFAULT_VMID})"
    )
    build_openwrt_parser.add_argument(
        "--password", help="Mot de passe root de la template"
    )
    build_openwrt_parser.set_defaults(func=run_build)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Opération annulée[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Erreur:[/red] {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

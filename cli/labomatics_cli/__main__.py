#!/usr/bin/env python3
"""CLI labomatics v0.4 - Orchestration centrale."""

import argparse
import sys
from rich.console import Console

from .commands.install import cmd_install

console = Console()


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
        help="Initialiser le cluster (créer VM centrale + stack Docker)",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les actions sans les exécuter",
    )
    install_parser.add_argument(
        "--hostname",
        default="labomatics",
        help="Nom d'hôte de la VM (défaut: labomatics)",
    )
    install_parser.add_argument(
        "--domain",
        default="lab.local",
        help="Domaine (défaut: lab.local)",
    )
    install_parser.add_argument(
        "--storage",
        help="Stockage partagé pour la VM (ex: local-lvm, ceph-store)",
    )
    install_parser.set_defaults(func=cmd_install)

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
        return 1


if __name__ == "__main__":
    sys.exit(main())

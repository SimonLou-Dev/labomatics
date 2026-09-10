#!/usr/bin/env python3
"""CLI labomatics v0.4 - Orchestration centrale."""

import argparse
import sys
import warnings

from rich.console import Console

from .commands.install import cmd_install
from .commands.templates import cmd_templates

# Suppress SSL warnings for self-signed certs (Proxmox, etc)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

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
        help="Initialiser le cluster central",
    )
    tempaltes_parser = subparsers.add_parser(
        "template",
        help="Gestion des templates",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les actions sans les exécuter",
    )
    install_parser.set_defaults(func=cmd_install)
    tempaltes_parser.set_defaults(func=cmd_templates)

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

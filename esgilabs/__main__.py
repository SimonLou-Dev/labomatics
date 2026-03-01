#!/usr/bin/env python3
"""
esgilabs — CLI Proxmox pilotée par CSV étudiant.

Commandes disponibles :
  apply        Synchronise Proxmox avec le CSV (diff + confirmation + apply)
  diff         Affiche le diff CSV ↔ Proxmox sans rien modifier
  pools        Liste les pools gérés par ce script
  zones        Liste les zones SDN du cluster
  vnets        Liste les VNets SDN (option : --zone)
  vms          Liste les VMs des pools gérés (option : --pool)
  find         Recherche un étudiant par IP WAN, VNet ou nom d'utilisateur
  credentials  Affiche les credentials générés (credentials.csv)
"""

import sys
import argparse

from rich.console import Console

from .commands import (
    cmd_apply,
    cmd_credentials,
    cmd_diff,
    cmd_find,
    cmd_pools,
    cmd_vnets,
    cmd_vms,
    cmd_zones,
)

console = Console()


def main() -> None:
    """Point d'entrée du CLI ``python -m esgilabs``."""
    parser = argparse.ArgumentParser(
        prog="python -m esgilabs",
        description="esgilabs — CLI Proxmox pilotée par CSV étudiant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            f"  {line}" for line in __doc__.strip().splitlines()
            if line.startswith("  ")
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<commande>")
    sub.required = True

    p = sub.add_parser("apply", help="Synchronise Proxmox avec le CSV")
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")

    sub.add_parser("diff",        help="Diff CSV ↔ Proxmox (lecture seule)")
    sub.add_parser("pools",       help="Liste les pools gérés")
    sub.add_parser("zones",       help="Liste les zones SDN")

    p = sub.add_parser("vnets",   help="Liste les VNets SDN")
    p.add_argument("--zone", metavar="ZONE", help="Filtrer par zone (défaut: zone du config)")

    p = sub.add_parser("vms",     help="Liste les VMs des pools gérés")
    p.add_argument("--pool", metavar="POOL", help="Filtrer par pool")

    p = sub.add_parser("find",    help="Recherche un étudiant par IP WAN, VNet ou nom")
    p.add_argument("query", metavar="QUERY",
                   help="IP WAN (172.16.0.18), VNet (vn00018) ou nom (mkorniev)")

    sub.add_parser("credentials", help="Affiche les credentials générés")

    args = parser.parse_args()

    dispatch = {
        "apply":       cmd_apply,
        "diff":        cmd_diff,
        "pools":       cmd_pools,
        "zones":       cmd_zones,
        "vnets":       cmd_vnets,
        "vms":         cmd_vms,
        "find":        cmd_find,
        "credentials": cmd_credentials,
    }

    try:
        dispatch[args.command](args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompu.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ {e}[/red]")
        raise


if __name__ == "__main__":
    main()

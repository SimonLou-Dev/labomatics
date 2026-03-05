#!/usr/bin/env python3
"""
labomatics — CLI Proxmox pilotée par CSV étudiant.

Commandes disponibles :
  apply          Synchronise Proxmox avec le CSV (diff + confirmation + apply)
  diff           Affiche le diff CSV ↔ Proxmox sans rien modifier
  pools          Liste les pools gérés
  zones          Liste les zones SDN
  vnets          Liste les VNets SDN (--zone pour filtrer)
  vms            Liste les VMs des pools gérés (--pool pour filtrer)
  find           Recherche un étudiant par IP, VNet ou nom
  credentials    Affiche les credentials générés (credentials.csv)
  ips            État des pools IP (WAN et VXLAN) avec % d'utilisation
  status         Ressources CPU/RAM/disk par étudiant vs flavor
  recreate       Recrée la VM OpenWrt d'un étudiant (--yes pour sans confirmation)
  build-template Construit une template via Packer + provisioning
  build-openwrt  Crée la template OpenWrt sur le nœud Proxmox local (root)
  destroy-all    Supprime toutes les ressources étudiants gérées
  init           Initialise /etc/labomatics/ avec les configs par défaut
"""

import argparse
import sys

from rich.console import Console

from .commands import (
    cmd_apply,
    cmd_build_openwrt,
    cmd_build_template,
    cmd_credentials,
    cmd_destroy_all,
    cmd_diff,
    cmd_find,
    cmd_init,
    cmd_ips,
    cmd_pools,
    cmd_recreate,
    cmd_status,
    cmd_vms,
    cmd_vnets,
    cmd_zones,
)

console = Console()


def main() -> None:
    """Point d'entrée du CLI ``labomatics``."""
    parser = argparse.ArgumentParser(
        prog="labomatics",
        description="labomatics — CLI Proxmox pilotée par CSV étudiant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            f"  {line}" for line in __doc__.strip().splitlines() if line.startswith("  ")
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<commande>")
    sub.required = True

    # apply / diff
    p = sub.add_parser("apply", help="Synchronise Proxmox avec le CSV")
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")

    sub.add_parser("diff", help="Diff CSV ↔ Proxmox (lecture seule)")

    # inspection
    sub.add_parser("pools", help="Liste les pools gérés")
    sub.add_parser("zones", help="Liste les zones SDN")

    p = sub.add_parser("vnets", help="Liste les VNets SDN")
    p.add_argument("--zone", metavar="ZONE", help="Filtrer par zone")

    p = sub.add_parser("vms", help="Liste les VMs des pools gérés")
    p.add_argument("--pool", metavar="POOL", help="Filtrer par pool")

    # recherche
    p = sub.add_parser("find", help="Recherche un étudiant par IP, VNet ou nom")
    p.add_argument("query", metavar="QUERY", help="IP WAN, VNet (vn00018) ou nom d'utilisateur")

    # credentials
    sub.add_parser("credentials", help="Affiche les credentials générés")

    # ips / status
    sub.add_parser("ips", help="État des pools IP (WAN/VXLAN) avec utilisation")
    sub.add_parser("status", help="Ressources CPU/RAM/disk par étudiant vs flavor")

    # recreate
    p = sub.add_parser("recreate", help="Recrée la VM OpenWrt d'un étudiant")
    p.add_argument("nom", metavar="NOM", help="Nom de l'étudiant (login Proxmox)")
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")

    # build-template
    p = sub.add_parser("build-template", help="Construit une template (Packer + provisioning)")
    p.add_argument("name", metavar="NOM", nargs="?", help="Nom de la template (défaut: toutes)")
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")

    # build-openwrt
    p = sub.add_parser(
        "build-openwrt",
        help="Crée la template OpenWrt sur le nœud Proxmox local (root requis)",
    )
    p.add_argument("--version", default="23.05.5", metavar="VERSION", help="Version OpenWrt (défaut: 23.05.5)")
    p.add_argument("--vmid", type=int, default=90200, metavar="VMID", help="VMID de la template (défaut: 90200)")
    p.add_argument("--storage", default="local-lvm", metavar="STORAGE", help="Stockage cible (défaut: local-lvm)")
    p.add_argument("--password", default="openwrt", metavar="PASSWORD", help="Mot de passe root OpenWrt (défaut: openwrt)")
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")

    # destroy-all
    p = sub.add_parser("destroy-all", help="Supprime toutes les ressources étudiants gérées")
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")

    # init
    p = sub.add_parser("init", help="Initialise /etc/labomatics/ avec les configs par défaut")
    p.add_argument("--dir", metavar="DIR", help="Répertoire cible (défaut: /etc/labomatics)")

    args = parser.parse_args()

    dispatch = {
        "apply": cmd_apply,
        "diff": cmd_diff,
        "pools": cmd_pools,
        "zones": cmd_zones,
        "vnets": cmd_vnets,
        "vms": cmd_vms,
        "find": cmd_find,
        "credentials": cmd_credentials,
        "ips": cmd_ips,
        "status": cmd_status,
        "recreate": cmd_recreate,
        "build-template": cmd_build_template,
        "build-openwrt": cmd_build_openwrt,
        "destroy-all": cmd_destroy_all,
        "init": cmd_init,
    }

    try:
        dispatch[args.command](args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompu.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

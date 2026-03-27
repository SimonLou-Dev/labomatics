#!/usr/bin/env python3
"""
labomatics — CLI Proxmox pilotée par CSV étudiant.

Groupes de commandes :
  setup              Assistant d'installation interactif
  student            Gestion des étudiants (apply/diff/deploy/status…)
  pool               Gestion des pools et des IPs
  sdn                Inspection SDN (zones, vnets)
  template           Construction des templates Proxmox

Exemples :
  labomatics setup
  labomatics student apply
  labomatics student diff --classe M1_SRC
  labomatics student deploy -f tp.yaml
  labomatics pool list
  labomatics sdn vnets
  labomatics template build
"""

import argparse
import sys

from rich.console import Console

from .commands import (
    cmd_apply,
    cmd_build_openwrt,
    cmd_build_template,
    cmd_credentials,
    cmd_deploy,
    cmd_destroy_all,
    cmd_diff,
    cmd_find,
    cmd_ips,
    cmd_pools,
    cmd_recreate,
    cmd_setup,
    cmd_status,
    cmd_undeploy,
    cmd_vms,
    cmd_vnets,
    cmd_zones,
)

console = Console()


def _add_classe(p: argparse.ArgumentParser) -> None:
    p.add_argument("--classe", metavar="CLASSE", help="Filtrer par classe (ex: M1_SRC)")


def _add_yes(p: argparse.ArgumentParser) -> None:
    p.add_argument("--yes", "-y", action="store_true", help="Pas de confirmation interactive")


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
    sub = parser.add_subparsers(dest="group", metavar="<groupe>")
    sub.required = True

    # ── setup ─────────────────────────────────────────────────────────────────

    p = sub.add_parser("setup", help="Assistant d'installation interactif")
    p.add_argument(
        "--dir", metavar="DIR", help="Répertoire de configuration (défaut: /etc/labomatics)"
    )

    # ── student ───────────────────────────────────────────────────────────────

    student_p = sub.add_parser("student", help="Gestion des étudiants")
    student_sub = student_p.add_subparsers(dest="command", metavar="<commande>")
    student_sub.required = True

    p = student_sub.add_parser("apply", help="Synchronise Proxmox avec le CSV")
    _add_yes(p)
    p.add_argument(
        "--recheck-all",
        action="store_true",
        help="Recrée users/tokens/ACL manquants pour tous les étudiants",
    )
    _add_classe(p)

    p = student_sub.add_parser("diff", help="Diff CSV ↔ Proxmox (lecture seule)")
    _add_classe(p)

    p = student_sub.add_parser("list", help="Liste les VMs des pools étudiants")
    p.add_argument("--pool", metavar="POOL", help="Filtrer par pool")
    _add_classe(p)

    p = student_sub.add_parser("status", help="Ressources CPU/RAM/disk par étudiant vs flavor")
    _add_classe(p)

    p = student_sub.add_parser("find", help="Recherche un étudiant par IP, VNet ou nom")
    p.add_argument("query", metavar="QUERY", help="IP WAN, VNet (vn00018) ou nom d'utilisateur")
    _add_classe(p)

    p = student_sub.add_parser("creds", help="Affiche les credentials étudiants")
    _add_classe(p)

    p = student_sub.add_parser("recreate", help="Recrée la VM OpenWrt d'un étudiant")
    p.add_argument("nom", metavar="NOM", help="Login de l'étudiant")
    _add_yes(p)

    p = student_sub.add_parser("deploy", help="Déploie les VMs d'un TP depuis un fichier YAML")
    p.add_argument("-f", "--file", required=True, metavar="FILE", help="Fichier TP YAML")
    p.add_argument(
        "--workers", type=int, default=2, metavar="N", help="Workers parallèles (défaut: 2)"
    )
    _add_yes(p)

    p = student_sub.add_parser("undeploy", help="Supprime toutes les VMs d'un TP")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("-f", "--file", metavar="FILE", help="Fichier TP YAML")
    grp.add_argument("--tp", metavar="NOM", help="Nom du TP (sans fichier)")
    p.add_argument(
        "--workers", type=int, default=2, metavar="N", help="Workers parallèles (défaut: 2)"
    )
    _add_yes(p)

    p = student_sub.add_parser("destroy", help="Supprime toutes les ressources étudiants gérées")
    _add_yes(p)

    # ── pool ──────────────────────────────────────────────────────────────────

    pool_p = sub.add_parser("pool", help="Gestion des pools et des IPs")
    pool_sub = pool_p.add_subparsers(dest="command", metavar="<commande>")
    pool_sub.required = True

    pool_sub.add_parser("list", help="Liste les pools gérés")
    pool_sub.add_parser("ips", help="État des pools IP (WAN/VXLAN) avec utilisation")

    # ── sdn ───────────────────────────────────────────────────────────────────

    sdn_p = sub.add_parser("sdn", help="Inspection SDN")
    sdn_sub = sdn_p.add_subparsers(dest="command", metavar="<commande>")
    sdn_sub.required = True

    sdn_sub.add_parser("zones", help="Liste les zones SDN")

    p = sdn_sub.add_parser("vnets", help="Liste les VNets SDN")
    p.add_argument("--zone", metavar="ZONE", help="Filtrer par zone")

    # ── template ──────────────────────────────────────────────────────────────

    template_p = sub.add_parser("template", help="Construction des templates Proxmox")
    template_sub = template_p.add_subparsers(dest="command", metavar="<commande>")
    template_sub.required = True

    p = template_sub.add_parser("build", help="Construit les templates cloud-init (infra.yaml)")
    p.add_argument(
        "names",
        metavar="NOMS",
        nargs="?",
        help="Noms séparés par ',' ou '*' pour toutes (défaut: toutes)",
    )
    _add_yes(p)

    p = template_sub.add_parser("build-openwrt", help="Construit la template OpenWrt")
    p.add_argument("--version", default=None, metavar="VERSION", help="Version OpenWrt")
    p.add_argument("--vmid", type=int, default=None, metavar="VMID", help="VMID cible")
    p.add_argument("--storage", default=None, metavar="STORAGE", help="Stockage cible")
    p.add_argument("--password", default="openwrt", metavar="PASSWORD", help="Mot de passe root")
    p.add_argument(
        "--template-pool",
        default="template",
        metavar="POOL",
        help="Pool template (défaut: template)",
    )
    _add_yes(p)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    args = parser.parse_args()

    student_dispatch = {
        "apply": cmd_apply,
        "diff": cmd_diff,
        "list": cmd_vms,
        "status": cmd_status,
        "find": cmd_find,
        "creds": cmd_credentials,
        "recreate": cmd_recreate,
        "deploy": cmd_deploy,
        "undeploy": cmd_undeploy,
        "destroy": cmd_destroy_all,
    }
    pool_dispatch = {
        "list": cmd_pools,
        "ips": cmd_ips,
    }
    sdn_dispatch = {
        "zones": cmd_zones,
        "vnets": cmd_vnets,
    }
    template_dispatch = {
        "build": cmd_build_template,
        "build-openwrt": cmd_build_openwrt,
    }

    group_dispatch = {
        "setup": (cmd_setup, None),
        "student": (None, student_dispatch),
        "pool": (None, pool_dispatch),
        "sdn": (None, sdn_dispatch),
        "template": (None, template_dispatch),
    }

    try:
        top_fn, sub_dispatch = group_dispatch[args.group]
        if top_fn is not None:
            top_fn(args)
        else:
            sub_dispatch[args.command](args)  # type: ignore[index]
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompu.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

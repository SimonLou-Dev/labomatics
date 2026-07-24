#!/usr/bin/env python3
"""
labomatics — CLI Proxmox pilotée par CSV étudiant.

Groupes de commandes :
  setup              Assistant d'installation interactif
  student            Gestion des étudiants et de leurs VMs
  pool               Pools Proxmox gérés par labomatics
  network            Réseau : zones SDN, VNets, adresses IP
  template           Construction des templates Proxmox

Exemples :
  labomatics setup
  labomatics student apply
  labomatics student diff --classe M1_SRC
  labomatics student deploy -f tp.yaml
  labomatics pool list
  labomatics network vnets
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
    p.add_argument("--yes", "-y", action="store_true", help="Sans confirmation interactive")


def _print_overview() -> None:
    console.print("\n[bold cyan]labomatics[/bold cyan] — CLI Proxmox pilotée par CSV étudiant\n")
    console.print("[bold]Groupes de commandes :[/bold]\n")
    rows = [
        ("setup", "Assistant d'installation interactif"),
        ("student", "apply  diff  list  status  find  creds  recreate  destroy"),
        ("tp", "deploy  undeploy               — déploiement de TPs"),
        ("pool", "list                         — pools Proxmox gérés par labomatics"),
        ("network", "zones  vnets  ips           — SDN, VNets et adresses IP"),
        ("template", "build  openwrt             — construction des templates Proxmox"),
    ]
    for group, cmds in rows:
        console.print(f"  [cyan]{group:<10}[/cyan]  {cmds}")
    console.print()
    console.print(
        "  [dim]student list[/dim]  → VMs de chaque étudiant  |  "
        "[dim]pool list[/dim]  → pools Proxmox et leurs quotas"
    )
    console.print("\n[bold]Utilisation :[/bold]")
    console.print("  labomatics [bold]<groupe>[/bold] <commande> [options]")
    console.print("  labomatics [bold]<groupe>[/bold] --help\n")
    console.print("[bold]Exemples :[/bold]")
    console.print("  labomatics [cyan]setup[/cyan]")
    console.print("  labomatics [cyan]student[/cyan] apply")
    console.print("  labomatics [cyan]student[/cyan] diff --classe M1_SRC")
    console.print("  labomatics [cyan]network[/cyan] vnets")
    console.print("  labomatics [cyan]template[/cyan] build\n")


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
    sub.required = False

    # ── setup ─────────────────────────────────────────────────────────────────

    p = sub.add_parser(
        "setup",
        help="Assistant d'installation interactif",
        description=(
            "Configure labomatics pas à pas : credentials Proxmox, fichiers de configuration, "
            "vérification de la connexion, stockage, SDN, pool template et template OpenWrt."
        ),
    )
    p.add_argument(
        "--dir",
        metavar="DIR",
        help="Répertoire de configuration (défaut : /etc/labomatics)",
    )

    # ── student ───────────────────────────────────────────────────────────────

    student_p = sub.add_parser(
        "student",
        help="Gestion des étudiants et de leurs VMs",
        description=(
            "Commandes de gestion du cycle de vie des étudiants : provisionnement, "
            "inspection des VMs, credentials, déploiement de TPs."
        ),
    )
    student_sub = student_p.add_subparsers(dest="command", metavar="<commande>")
    student_sub.required = True

    p = student_sub.add_parser(
        "apply",
        help="Provisionne ou met à jour les ressources de chaque étudiant",
        description=(
            "Compare le CSV avec l'état Proxmox et crée/supprime pools, VNets, VMs OpenWrt, "
            "utilisateurs et ACL pour chaque étudiant. Affiche un diff avant de confirmer."
        ),
    )
    _add_yes(p)
    p.add_argument(
        "--recheck-all",
        action="store_true",
        help="Recrée les users/tokens/ACL manquants pour tous les étudiants (sans recréer les VMs)",
    )
    _add_classe(p)

    p = student_sub.add_parser(
        "diff",
        help="Aperçu des changements à apporter (lecture seule, sans modification)",
        description=(
            "Affiche ce que 'apply' ferait : étudiants à ajouter, à supprimer, "
            "et ressources manquantes. Aucune modification n'est effectuée."
        ),
    )
    _add_classe(p)

    p = student_sub.add_parser(
        "list",
        help="Liste les VMs présentes dans les pools étudiants",
        description=(
            "Affiche toutes les VMs (VMID, nom, statut, nœud) pour chaque pool étudiant géré. "
            "Différent de 'pool list' qui liste les pools eux-mêmes et leurs quotas."
        ),
    )
    p.add_argument("--pool", metavar="POOL", help="Filtrer par pool")
    _add_classe(p)

    p = student_sub.add_parser(
        "status",
        help="Consommation CPU/RAM/disk de chaque étudiant vs son flavor",
        description=(
            "Affiche pour chaque étudiant la consommation actuelle de ressources "
            "et la compare aux limites définies par son flavor (CO1, CO2…)."
        ),
    )
    _add_classe(p)

    p = student_sub.add_parser(
        "find",
        help="Recherche un étudiant par IP WAN, VNet ou login",
        description="Identifie l'étudiant propriétaire d'une IP WAN, d'un VNet (ex: vn00018) ou d'un login.",
    )
    p.add_argument(
        "query",
        metavar="QUERY",
        help="IP WAN (172.16.0.x), identifiant VNet (vn00018) ou login étudiant",
    )
    _add_classe(p)

    p = student_sub.add_parser(
        "creds",
        help="Affiche les credentials Proxmox générés pour chaque étudiant",
        description=(
            "Affiche login, mot de passe API token, IP WAN et VNet de chaque étudiant "
            "depuis le fichier credentials.csv."
        ),
    )
    _add_classe(p)

    p = student_sub.add_parser(
        "recreate",
        help="Supprime et recrée la VM OpenWrt d'un étudiant",
        description=(
            "Supprime la VM OpenWrt existante de l'étudiant et en crée une nouvelle "
            "depuis la template. Utile après une corruption ou une mauvaise config réseau."
        ),
    )
    p.add_argument("nom", metavar="NOM", help="Login de l'étudiant (ex: jdupont)")
    _add_yes(p)

    p = student_sub.add_parser(
        "destroy",
        help="Supprime TOUTES les ressources étudiants gérées par labomatics",
        description=(
            "Supprime tous les pools, VNets, VMs, utilisateurs et ACL créés par labomatics. "
            "Action irréversible — une confirmation est demandée."
        ),
    )
    _add_yes(p)

    # ── tp ────────────────────────────────────────────────────────────────────

    tp_p = sub.add_parser(
        "tp",
        help="Déploiement de TPs (travaux pratiques)",
        description=(
            "Déploie ou supprime les VMs d'un TP dans les pools étudiants. "
            "Les VMs sont identifiées par un tag Proxmox et un marker dans leur description."
        ),
    )
    tp_sub = tp_p.add_subparsers(dest="command", metavar="<commande>")
    tp_sub.required = True

    p = tp_sub.add_parser(
        "deploy",
        help="Déploie les VMs d'un TP pour les étudiants ciblés",
        description=(
            "Clone les VMs définies dans un fichier TP YAML dans le pool de chaque étudiant. "
            "Idempotent : les VMs déjà déployées avec la même configuration sont ignorées, "
            "celles dont la config a changé sont supprimées et recrées."
        ),
    )
    p.add_argument("-f", "--file", required=True, metavar="FILE", help="Fichier TP YAML")
    _add_yes(p)

    p = tp_sub.add_parser(
        "undeploy",
        help="Supprime toutes les VMs d'un TP déployé",
        description=(
            "Supprime toutes les VMs portant le tag du TP dans tous les pools étudiants. "
            "N'affecte pas les VMs OpenWrt ni les autres ressources étudiants."
        ),
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("-f", "--file", metavar="FILE", help="Fichier TP YAML (lit le nom du TP)")
    grp.add_argument("--tp", metavar="NOM", help="Nom du TP (sans fichier YAML)")
    _add_yes(p)

    # ── pool ──────────────────────────────────────────────────────────────────

    pool_p = sub.add_parser(
        "pool",
        help="Pools Proxmox gérés par labomatics",
        description=(
            "Inspecte les pools Proxmox créés par labomatics, leurs quotas CPU/RAM/disk "
            "et le nombre de VMs qu'ils contiennent. "
            "Pour voir les VMs à l'intérieur des pools, utilisez 'student list'."
        ),
    )
    pool_sub = pool_p.add_subparsers(dest="command", metavar="<commande>")
    pool_sub.required = True

    pool_sub.add_parser(
        "list",
        help="Liste les pools gérés avec leurs quotas et le nombre de VMs",
        description=(
            "Affiche chaque pool étudiant géré par labomatics avec ses limites "
            "CPU/RAM/disk et le nombre de VMs présentes. "
            "Différent de 'student list' qui détaille les VMs à l'intérieur."
        ),
    )

    # ── network ───────────────────────────────────────────────────────────────

    network_p = sub.add_parser(
        "network",
        help="Réseau : zones SDN, VNets et utilisation des adresses IP",
        description=(
            "Inspecte l'infrastructure réseau Proxmox SDN : zones VXLAN, VNets par étudiant "
            "et état des pools d'adresses IP (WAN et VXLAN)."
        ),
    )
    network_sub = network_p.add_subparsers(dest="command", metavar="<commande>")
    network_sub.required = True

    network_sub.add_parser(
        "zones",
        help="Liste les zones SDN configurées dans Proxmox",
        description="Affiche toutes les zones SDN (VXLAN, Simple…) du datacenter Proxmox.",
    )

    p = network_sub.add_parser(
        "vnets",
        help="Liste les VNets SDN (un par étudiant)",
        description=(
            "Affiche tous les VNets dans les zones SDN gérées. "
            "Chaque étudiant dispose d'un VNet dédié (ex: vn00018)."
        ),
    )
    p.add_argument("--zone", metavar="ZONE", help="Filtrer par zone SDN (ex: esgilab)")

    network_sub.add_parser(
        "ips",
        help="Utilisation des pools IP WAN et VXLAN",
        description=(
            "Affiche le taux d'utilisation des plages IP WAN et VXLAN définies dans infra.yaml, "
            "avec les adresses allouées et disponibles."
        ),
    )

    # ── template ──────────────────────────────────────────────────────────────

    template_p = sub.add_parser(
        "template",
        help="Construction des templates Proxmox",
        description=(
            "Construit des templates VM Proxmox à partir d'images cloud : "
            "Linux cloud-init (Ubuntu, Debian, Fedora…) ou OpenWrt (routeur étudiant)."
        ),
    )
    template_sub = template_p.add_subparsers(dest="command", metavar="<commande>")
    template_sub.required = True

    p = template_sub.add_parser(
        "build",
        help="Construit les templates Linux cloud-init définies dans infra.yaml",
        description=(
            "Télécharge l'image cloud, installe les packages via virt-customize, "
            "démarre la VM pour initialiser cloud-init, puis convertit en template Proxmox."
        ),
    )
    p.add_argument(
        "names",
        metavar="NOMS",
        nargs="?",
        help="Nom(s) de template séparés par ',' — omis = toutes les templates (ex: ubuntu-25.10,debian-13)",
    )
    _add_yes(p)

    p = template_sub.add_parser(
        "openwrt",
        help="Construit la template OpenWrt (routeur étudiant)",
        description=(
            "Télécharge le firmware OpenWrt, crée une VM Proxmox et la convertit en template. "
            "Cette template est clonée pour chaque étudiant lors de 'student apply'."
        ),
    )
    p.add_argument("--version", default=None, metavar="VERSION", help="Version OpenWrt à utiliser")
    p.add_argument("--vmid", type=int, default=None, metavar="VMID", help="VMID à assigner")
    p.add_argument("--storage", default=None, metavar="STORAGE", help="Stockage cible")
    p.add_argument(
        "--password", default="openwrt", metavar="PASSWORD", help="Mot de passe root OpenWrt"
    )
    p.add_argument(
        "--template-pool",
        default="template",
        metavar="POOL",
        help="Pool Proxmox où ranger la template (défaut : template)",
    )
    _add_yes(p)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    args = parser.parse_args()

    if not getattr(args, "group", None):
        _print_overview()
        sys.exit(0)

    student_dispatch = {
        "apply": cmd_apply,
        "diff": cmd_diff,
        "list": cmd_vms,
        "status": cmd_status,
        "find": cmd_find,
        "creds": cmd_credentials,
        "recreate": cmd_recreate,
        "destroy": cmd_destroy_all,
    }
    tp_dispatch = {
        "deploy": cmd_deploy,
        "undeploy": cmd_undeploy,
    }
    pool_dispatch = {
        "list": cmd_pools,
    }
    network_dispatch = {
        "zones": cmd_zones,
        "vnets": cmd_vnets,
        "ips": cmd_ips,
    }
    template_dispatch = {
        "build": cmd_build_template,
        "openwrt": cmd_build_openwrt,
    }

    group_dispatch = {
        "setup": (cmd_setup, None),
        "student": (None, student_dispatch),
        "tp": (None, tp_dispatch),
        "pool": (None, pool_dispatch),
        "network": (None, network_dispatch),
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

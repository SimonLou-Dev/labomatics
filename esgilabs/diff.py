#!/usr/bin/env python3
"""
Calcul et affichage des différences entre l'état CSV et l'état Proxmox.

Le diff compare la liste des étudiants du CSV (état désiré) avec les pools
gérés existants dans Proxmox (état courant) pour déterminer :

- ``to_add`` : étudiants présents dans le CSV mais sans pool dans Proxmox
- ``to_remove`` : pools Proxmox gérés correspondant à des étudiants absents du CSV

Ce module est purement fonctionnel (pas d'appels API) et peut être utilisé
pour un aperçu sans modification (commande ``diff``).
"""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from .config import InfraConfig
    from .students import Student


def compute_diff(
    managed_pools: list[dict],
    students: list["Student"],
) -> tuple[list["Student"], list[dict]]:
    """Calcule les ajouts et suppressions à appliquer.

    La correspondance est faite sur ``student.pool_name()`` (= ``student.nom``)
    et ``pool["poolid"]``.

    Args:
        managed_pools: Pools Proxmox gérés (retournés par :func:`~esgilabs.proxmox.list_managed_pools`).
        students: Liste des étudiants chargés depuis le CSV.

    Returns:
        Tuple ``(to_add, to_remove)`` :

        - ``to_add`` : étudiants à créer dans Proxmox
        - ``to_remove`` : pools Proxmox à supprimer
    """
    current = {p["poolid"] for p in managed_pools}
    desired = {s.pool_name() for s in students}
    to_add    = [s for s in students if s.pool_name() not in current]
    to_remove = [p for p in managed_pools if p["poolid"] not in desired]
    return to_add, to_remove


def print_diff(
    to_add: list["Student"],
    to_remove: list[dict],
    config: "InfraConfig",
    console: Console,
) -> None:
    """Affiche un tableau Rich coloré des changements à appliquer.

    Les ajouts sont affichés en vert (``+``), les suppressions en rouge (``−``).
    Si aucun changement n'est détecté, un message de confirmation est affiché.

    Args:
        to_add: Étudiants à créer.
        to_remove: Pools à supprimer.
        config: Configuration de l'infrastructure (pour les subnets).
        console: Instance :class:`rich.console.Console` pour l'affichage.
    """
    if not to_add and not to_remove:
        console.print("[bold green]✓ Rien à faire — Proxmox conforme au CSV[/bold green]")
        return

    wan_subnet = config.openwrt.network.wan_subnet
    vxlan_pool = config.openwrt.network.vxlan_pool

    table = Table(
        show_header=True, header_style="bold white",
        title="[bold]Changements à appliquer[/bold]", title_justify="left",
    )
    table.add_column("", width=6)
    table.add_column("Pool / Étudiant", style="cyan", no_wrap=True)
    table.add_column("VMID", justify="right")
    table.add_column("WAN IP")
    table.add_column("VXLAN subnet")
    table.add_column("VNet")

    for s in to_add:
        table.add_row(
            "[bold green]+[/bold green]",
            s.pool_name(),
            str(s.vmid(config.openwrt.vmid_start)),
            s.wan_ip(wan_subnet),
            s.vxlan_subnet(vxlan_pool),
            s.vnet_name(),
        )
    for p in to_remove:
        table.add_row(
            "[bold red]−[/bold red]",
            p["poolid"], "—", "—", "—", "—",
        )

    console.print(table)
    console.print(
        f"  [green]+ {len(to_add)} à créer[/green]   "
        f"[red]− {len(to_remove)} à supprimer[/red]\n"
    )

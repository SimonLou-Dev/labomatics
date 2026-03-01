#!/usr/bin/env python3
"""
Commandes d'inspection du cluster Proxmox (lecture seule).

Ces commandes ne modifient rien — elles affichent l'état courant du cluster :

- ``pools``  : pools gérés par ce script
- ``zones``  : zones SDN du cluster
- ``vnets``  : VNets d'une zone SDN
- ``vms``    : VMs des pools gérés
"""

import sys

from rich.console import Console
from rich.table import Table

from ._helpers import make_connection
from ..proxmox import (
    get_pool_lxcs,
    get_pool_vms,
    list_managed_pools,
    list_vnets_in_zone,
)

console = Console()


def cmd_pools(_) -> None:
    """Affiche tous les pools Proxmox gérés par ce script avec leurs membres."""
    proxmox, _ = make_connection()
    pools = list_managed_pools(proxmox)

    if not pools:
        console.print("[dim]Aucun pool géré.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Pools gérés")
    table.add_column("Pool", style="cyan")
    table.add_column("VMs", justify="right")
    table.add_column("LXC", justify="right")
    table.add_column("Membres QEMU", style="dim")

    for pool in sorted(pools, key=lambda p: p["poolid"]):
        pid = pool["poolid"]
        try:
            vms = get_pool_vms(proxmox, pid)
            lxcs = get_pool_lxcs(proxmox, pid)
            members_str = ", ".join(m.get("name", str(m.get("vmid"))) for m in vms)
        except Exception:
            vms, lxcs, members_str = [], [], "?"
        table.add_row(pid, str(len(vms)), str(len(lxcs)), members_str or "—")

    console.print(table)
    console.print(f"\n  {len(pools)} pool(s)\n")


def cmd_zones(_) -> None:
    """Affiche toutes les zones SDN du cluster avec leur type et état."""
    proxmox, _ = make_connection()
    zones = proxmox.cluster.sdn.zones.get()

    if not zones:
        console.print("[dim]Aucune zone SDN.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Zones SDN")
    table.add_column("Zone", style="cyan")
    table.add_column("Type")
    table.add_column("State")
    table.add_column("Peers / Options", style="dim")

    for z in sorted(zones, key=lambda x: x.get("zone", "")):
        state = z.get("state", "—")
        state_fmt = f"[green]{state}[/green]" if state == "ok" else f"[yellow]{state}[/yellow]"
        table.add_row(
            z.get("zone", "—"),
            z.get("type", "—"),
            state_fmt,
            z.get("peers") or z.get("nodes") or "—",
        )

    console.print(table)


def cmd_vnets(args) -> None:
    """Affiche les VNets SDN, filtrés par zone si ``--zone`` est passé."""
    proxmox, cfg = make_connection()
    zone = args.zone or cfg.openwrt.network.zone_name
    vnets = list_vnets_in_zone(proxmox, zone)

    if not vnets:
        console.print(f"[dim]Aucun VNet dans la zone '{zone}'.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title=f"VNets — zone {zone}")
    table.add_column("VNet", style="cyan")
    table.add_column("Zone")
    table.add_column("Tag VXLAN", justify="right")
    table.add_column("Pool associé", style="dim")

    for v in sorted(vnets, key=lambda x: x.get("tag", 0)):
        table.add_row(
            v.get("vnet", "—"),
            v.get("zone", "—"),
            str(v.get("tag", "—")),
            v.get("alias") or v.get("comment") or "—",
        )

    console.print(table)
    console.print(f"\n  {len(vnets)} vnet(s)\n")


def cmd_vms(args) -> None:
    """Affiche les VMs QEMU des pools gérés, filtrées par ``--pool`` si précisé."""
    proxmox, _ = make_connection()

    if args.pool:
        try:
            members = get_pool_vms(proxmox, args.pool)
        except Exception as e:
            console.print(f"[red]❌ Pool '{args.pool}' introuvable : {e}[/red]")
            sys.exit(1)
        rows = [(m, args.pool) for m in members]
    else:
        rows = []
        for pool in sorted(list_managed_pools(proxmox), key=lambda p: p["poolid"]):
            try:
                for m in get_pool_vms(proxmox, pool["poolid"]):
                    rows.append((m, pool["poolid"]))
            except Exception:
                pass

    if not rows:
        console.print("[dim]Aucune VM trouvée.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="VMs gérées")
    table.add_column("VM", style="cyan", no_wrap=True)
    table.add_column("VMID", justify="right")
    table.add_column("Pool")
    table.add_column("Node")
    table.add_column("Status")

    for vm, pool_id in sorted(rows, key=lambda r: r[0].get("vmid", 0)):
        status = vm.get("status", "—")
        status_fmt = (
            f"[green]{status}[/green]" if status == "running"
            else f"[yellow]{status}[/yellow]"
        )
        table.add_row(
            vm.get("name", "—"),
            str(vm.get("vmid", "—")),
            pool_id,
            vm.get("node", "—"),
            status_fmt,
        )

    console.print(table)
    console.print(f"\n  {len(rows)} VM(s)\n")

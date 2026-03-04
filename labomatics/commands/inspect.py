#!/usr/bin/env python3
"""
Commandes d'inspection : pools, zones, vnets, vms.
"""

from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..proxmox import (
    get_pool_lxcs,
    get_pool_vms,
    list_managed_pools,
    list_vnets_in_zone,
)
from ._helpers import make_connection

console = Console()


def cmd_pools(args) -> None:
    """Liste les pools gérés par labomatics."""
    config = load_config()
    proxmox = make_connection()
    pools = list_managed_pools(proxmox)

    if not pools:
        console.print("[dim]Aucun pool géré.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Pools gérés")
    table.add_column("Pool", style="cyan")
    table.add_column("VMs", justify="right")
    table.add_column("LXC", justify="right")

    for p in sorted(pools, key=lambda x: x["poolid"]):
        pool_name = p["poolid"]
        vms = get_pool_vms(proxmox, pool_name)
        lxcs = get_pool_lxcs(proxmox, pool_name)
        table.add_row(pool_name, str(len(vms)), str(len(lxcs)))

    console.print(table)
    console.print(f"\n  {len(pools)} pool(s) géré(s)\n")


def cmd_zones(args) -> None:
    """Liste toutes les zones SDN du cluster."""
    proxmox = make_connection()
    zones = proxmox.cluster.sdn.zones().get()

    if not zones:
        console.print("[dim]Aucune zone SDN.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="Zones SDN")
    table.add_column("Zone", style="cyan")
    table.add_column("Type")
    table.add_column("MTU", justify="right")
    table.add_column("Peers")

    for z in sorted(zones, key=lambda x: x.get("zone", "")):
        table.add_row(
            z.get("zone", ""),
            z.get("type", ""),
            str(z.get("mtu", "—")),
            str(z.get("peers", "—")),
        )

    console.print(table)


def cmd_vnets(args) -> None:
    """Liste les VNets SDN (optionnel : --zone)."""
    config = load_config()
    proxmox = make_connection()
    zone_filter = getattr(args, "zone", None) or config.openwrt.network.zone_name

    vnets = list_vnets_in_zone(proxmox, zone_filter)
    if not vnets:
        console.print(f"[dim]Aucun VNet dans la zone '{zone_filter}'.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title=f"VNets — zone {zone_filter}")
    table.add_column("VNet", style="cyan")
    table.add_column("Tag VXLAN", justify="right")
    table.add_column("Alias")

    for v in sorted(vnets, key=lambda x: x.get("tag", 0)):
        table.add_row(
            v.get("vnet", ""),
            str(v.get("tag", "—")),
            v.get("alias", "—"),
        )

    console.print(table)
    console.print(f"\n  {len(vnets)} VNet(s)\n")


def cmd_vms(args) -> None:
    """Liste les VMs des pools gérés (optionnel : --pool)."""
    config = load_config()
    proxmox = make_connection()

    pool_filter = getattr(args, "pool", None)
    if pool_filter:
        pools = [{"poolid": pool_filter}]
    else:
        pools = list_managed_pools(proxmox)

    if not pools:
        console.print("[dim]Aucun pool géré.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", title="VMs — pools gérés")
    table.add_column("Pool", style="cyan")
    table.add_column("VM / LXC")
    table.add_column("VMID", justify="right")
    table.add_column("Nœud")
    table.add_column("Statut")
    table.add_column("Mémoire", justify="right")

    for p in sorted(pools, key=lambda x: x["poolid"]):
        pool_name = p["poolid"]
        members = get_pool_vms(proxmox, pool_name) + get_pool_lxcs(proxmox, pool_name)
        for m in sorted(members, key=lambda x: x.get("vmid", 0)):
            status = m.get("status", "—")
            status_str = (
                f"[green]{status}[/green]" if status == "running"
                else f"[dim]{status}[/dim]"
            )
            mem_mb = m.get("mem", 0) // (1024 * 1024)
            mem_max_mb = m.get("maxmem", 0) // (1024 * 1024)
            mem_str = f"{mem_mb}/{mem_max_mb} MB" if mem_max_mb else "—"
            table.add_row(
                pool_name,
                m.get("name", "—"),
                str(m.get("vmid", "—")),
                m.get("node", "—"),
                status_str,
                mem_str,
            )

    console.print(table)

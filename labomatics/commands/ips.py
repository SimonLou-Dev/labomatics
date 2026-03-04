#!/usr/bin/env python3
"""
Commande ``ips`` — état des pools IP (WAN et VXLAN).

Affiche les IPs WAN utilisées, disponibles et le % d'utilisation de chaque pool.
"""

from ipaddress import ip_network

from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..ip_pool import (
    get_available_wan_ips,
    get_used_vxlan_subnets,
    get_used_wan_ips,
)
from ._helpers import make_connection

console = Console()


def cmd_ips(args) -> None:
    """Affiche l'état d'utilisation des pools IP (WAN et VXLAN)."""
    config = load_config()
    proxmox = make_connection()

    # ── Pool WAN ──────────────────────────────────────────────────────────────
    wan_cfg = config.openwrt.network.wan_pool
    wan_net = ip_network(wan_cfg.network, strict=False)
    wan_total = wan_net.num_addresses - 2  # sans réseau et broadcast
    used_wan = get_used_wan_ips(proxmox, config)
    available_wan = get_available_wan_ips(proxmox, config)

    wan_used_count = len(used_wan)
    wan_available_count = len(available_wan)
    wan_pct = (wan_used_count / wan_total * 100) if wan_total else 0

    console.print()
    console.print("[bold cyan]═══ Pool WAN ═══[/bold cyan]")

    wan_table = Table(show_header=True, header_style="bold white")
    wan_table.add_column("Réseau WAN", style="cyan")
    wan_table.add_column("Gateway")
    wan_table.add_column("Total hôtes", justify="right")
    wan_table.add_column("Utilisées", justify="right")
    wan_table.add_column("Disponibles", justify="right")
    wan_table.add_column("Utilisation", justify="right")

    pct_color = "green" if wan_pct < 70 else "yellow" if wan_pct < 90 else "red"
    wan_table.add_row(
        wan_cfg.network,
        wan_cfg.gateway,
        str(wan_total),
        str(wan_used_count),
        str(wan_available_count),
        f"[{pct_color}]{wan_pct:.1f}%[/{pct_color}]",
    )
    console.print(wan_table)

    # Détail des IPs utilisées
    if used_wan:
        detail = Table(show_header=True, header_style="bold dim")
        detail.add_column("IP WAN utilisée", style="dim")
        detail.add_column("Prochaine IP libre")
        next_ip = str(available_wan[0]) if available_wan else "—"
        for i, ip in enumerate(sorted(used_wan)):
            detail.add_row(str(ip), next_ip if i == 0 else "")
        console.print(detail)

    # ── Pool VXLAN ────────────────────────────────────────────────────────────
    vxlan_cfg = config.openwrt.network.vxlan_pool
    vxlan_net = ip_network(vxlan_cfg.network, strict=False)
    vxlan_total = sum(1 for _ in vxlan_net.subnets(new_prefix=24))
    used_vxlan = get_used_vxlan_subnets(proxmox, config)
    vxlan_used_count = len(used_vxlan)
    vxlan_available = vxlan_total - vxlan_used_count
    vxlan_pct = (vxlan_used_count / vxlan_total * 100) if vxlan_total else 0

    console.print()
    console.print("[bold cyan]═══ Pool VXLAN (/24 par étudiant) ═══[/bold cyan]")

    vxlan_table = Table(show_header=True, header_style="bold white")
    vxlan_table.add_column("Pool VXLAN", style="cyan")
    vxlan_table.add_column("Subnets /24 total", justify="right")
    vxlan_table.add_column("Utilisés", justify="right")
    vxlan_table.add_column("Disponibles", justify="right")
    vxlan_table.add_column("Utilisation", justify="right")

    pct_color = "green" if vxlan_pct < 70 else "yellow" if vxlan_pct < 90 else "red"
    vxlan_table.add_row(
        vxlan_cfg.network,
        str(vxlan_total),
        str(vxlan_used_count),
        str(vxlan_available),
        f"[{pct_color}]{vxlan_pct:.1f}%[/{pct_color}]",
    )
    console.print(vxlan_table)

    if used_vxlan:
        detail2 = Table(show_header=True, header_style="bold dim")
        detail2.add_column("Subnets VXLAN utilisés", style="dim")
        for subnet in sorted(used_vxlan):
            detail2.add_row(str(subnet))
        console.print(detail2)

    console.print()

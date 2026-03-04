#!/usr/bin/env python3
"""
Commande ``status`` — état CPU/RAM/disk par étudiant (vs flavor).
"""

from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..ip_pool import get_vm_wan_ip
from ..proxmox import get_pool_lxcs, get_pool_vms, list_managed_pools
from ._helpers import load_students_from_config, make_connection

console = Console()


def _pct_bar(value: int, limit: int, unit: str = "") -> str:
    """Affiche une valeur avec la limite et le % colorisé."""
    if limit <= 0:
        return f"{value}{unit} / ∞"
    pct = value / limit * 100
    color = "green" if pct < 70 else "yellow" if pct < 90 else "bold red"
    return f"{value}{unit} / {limit}{unit} [{color}]({pct:.0f}%)[/{color}]"


def cmd_status(args) -> None:
    """Affiche l'état des ressources (CPU/RAM/disk) par étudiant vs flavor."""
    config = load_config()
    proxmox = make_connection()

    # Construire un index nom → étudiant
    try:
        students = load_students_from_config(config)
        student_map = {s.nom: s for s in students}
    except Exception:
        student_map = {}

    pools = list_managed_pools(proxmox)
    if not pools:
        console.print("[dim]Aucun pool géré.[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold magenta",
        title="État des ressources étudiants",
    )
    table.add_column("Étudiant", style="cyan", no_wrap=True)
    table.add_column("Flavor")
    table.add_column("IP WAN")
    table.add_column("CPU (running)", justify="right")
    table.add_column("RAM (running)", justify="right")
    table.add_column("Disk (total)", justify="right")
    table.add_column("VM / LXC", justify="right")

    for p in sorted(pools, key=lambda x: x["poolid"]):
        pool_name = p["poolid"]
        student = student_map.get(pool_name)
        flavor_name = student.flavor if student else "—"
        flavor = config.get_flavor(flavor_name) if student else None

        vms = get_pool_vms(proxmox, pool_name)
        lxcs = get_pool_lxcs(proxmox, pool_name)
        all_members = vms + lxcs

        # CPU et RAM : seulement pour les VMs running
        cpu_used_cores = sum(m.get("cpus", 0) for m in all_members if m.get("status") == "running")
        ram_used_mb = sum(
            m.get("maxmem", 0) for m in all_members if m.get("status") == "running"
        ) // (1024 * 1024)

        # Disk : toutes les VMs
        disk_used_gb = sum(m.get("disk", 0) for m in all_members) // (1024 * 1024 * 1024)

        # IP WAN depuis la première VM du pool
        wan_ip = "—"
        for vm in vms:
            ip = get_vm_wan_ip(proxmox, vm["node"], vm["vmid"])
            if ip:
                wan_ip = ip
                break

        vm_count = f"{len(vms)}V/{len(lxcs)}L"

        if flavor and flavor.cpu > 0:
            cpu_str = _pct_bar(cpu_used_cores, flavor.cpu, "c")
        else:
            cpu_str = f"{cpu_used_cores}c / ∞"

        if flavor and flavor.ram > 0:
            ram_str = _pct_bar(ram_used_mb, flavor.ram, "M")
        else:
            ram_str = f"{ram_used_mb}M / ∞"

        if flavor and flavor.disk > 0:
            disk_str = _pct_bar(disk_used_gb, flavor.disk, "G")
        else:
            disk_str = f"{disk_used_gb}G / ∞"

        table.add_row(
            pool_name,
            flavor_name,
            wan_ip,
            cpu_str,
            ram_str,
            disk_str,
            vm_count,
        )

    console.print(table)
    console.print(f"\n  {len(pools)} étudiant(s)\n")

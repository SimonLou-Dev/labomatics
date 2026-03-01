#!/usr/bin/env python3
"""
Commande ``find`` — recherche d'un étudiant par IP WAN, VNet ou nom.

Résout une requête textuelle vers un étudiant, puis affiche ses informations
réseau complètes et l'état live de sa VM sur le cluster Proxmox.

Formats de requête acceptés :
- IP WAN        ex. ``172.16.0.18``
- Nom de VNet   ex. ``vn00018``
- Nom étudiant  ex. ``mkorniev``
"""

import re
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ._helpers import load_students_from_config, make_connection
from ..proxmox import get_pool_vms, list_managed_pools
from ..students import Student

console = Console()


def resolve_student(
    query: str,
    students: list[Student],
    wan_subnet: str,
) -> tuple[Student | None, str]:
    """Résout une requête textuelle vers un étudiant.

    Args:
        query: Chaîne de recherche (IP WAN, nom de VNet ou nom d'utilisateur).
        students: Liste des étudiants chargés depuis le CSV.
        wan_subnet: Subnet WAN (pour calculer les IPs WAN de chaque étudiant).

    Returns:
        Tuple ``(student, kind)`` :

        - ``student`` : l'étudiant trouvé, ou ``None``
        - ``kind`` : type de recherche effectuée (``"IP WAN"``, ``"VNet"``, ``"nom"``)
    """
    q = query.strip()

    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', q):
        kind = "IP WAN"
        for s in students:
            try:
                if s.wan_ip(wan_subnet) == q:
                    return s, kind
            except ValueError:
                pass

    elif re.match(r'^vn\d+$', q, re.IGNORECASE):
        kind = "VNet"
        for s in students:
            if s.vnet_name().lower() == q.lower():
                return s, kind

    else:
        kind = "nom"
        for s in students:
            if s.nom.lower() == q.lower():
                return s, kind

    return None, kind


def cmd_find(args) -> None:
    """Recherche un étudiant et affiche ses informations réseau + état Proxmox."""
    proxmox, cfg = make_connection()
    students = load_students_from_config(cfg)

    wan_subnet = cfg.openwrt.network.wan_subnet
    vxlan_pool = cfg.openwrt.network.vxlan_pool
    vmid_start = cfg.openwrt.vmid_start

    student, kind = resolve_student(args.query, students, wan_subnet)

    if student is None:
        console.print(
            f"[red]❌ Aucun étudiant trouvé pour '{args.query}' (recherche par {kind})[/red]"
        )
        sys.exit(1)

    # ── Informations réseau (depuis le CSV + calcul) ───────────────────────
    try:
        wan_ip = student.wan_ip(wan_subnet)
        vxlan_subnet = student.vxlan_subnet(vxlan_pool)
        vxlan_ip = student.vxlan_ip(vxlan_pool)
        vxlan_gw = student.vxlan_gateway(vxlan_pool)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        sys.exit(1)

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan", no_wrap=True)
    grid.add_column()

    grid.add_row("Nom",           student.nom)
    grid.add_row("ID",            str(student.id))
    grid.add_row("Index CSV",     f"#{student.index}")
    grid.add_row("User Proxmox",  student.user_id())
    grid.add_row("VMID",          str(student.vmid(vmid_start)))
    grid.add_row("Pool",          student.pool_name())
    grid.add_row("WAN IP",        wan_ip)
    grid.add_row("VXLAN subnet",  vxlan_subnet)
    grid.add_row("VXLAN IP",      vxlan_ip)
    grid.add_row("VXLAN gateway", vxlan_gw)
    grid.add_row("VNet",          student.vnet_name())
    grid.add_row("VXLAN tag",     str(student.id))

    # ── État live Proxmox ─────────────────────────────────────────────────
    pool_exists = any(p["poolid"] == student.pool_name() for p in list_managed_pools(proxmox))
    pool_status = "[green]✓ existe[/green]" if pool_exists else "[red]✗ absent[/red]"
    grid.add_row("Pool Proxmox", pool_status)

    vm_status_str = "[dim]—[/dim]"
    if pool_exists:
        try:
            vms = get_pool_vms(proxmox, student.pool_name())
            if vms:
                st = vms[0].get("status", "?")
                node = vms[0].get("node", "?")
                vm_status_str = (
                    f"[green]{st}[/green] ({node})" if st == "running"
                    else f"[yellow]{st}[/yellow] ({node})"
                )
            else:
                vm_status_str = "[red]✗ VM absente[/red]"
        except Exception:
            vm_status_str = "[yellow]erreur[/yellow]"
    grid.add_row("VM status", vm_status_str)

    console.print(Panel(grid, title=f"[bold]{student.nom}[/bold]", expand=False))

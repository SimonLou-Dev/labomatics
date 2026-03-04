#!/usr/bin/env python3
"""
Commande ``find`` — recherche d'un étudiant par IP, VNet ou nom.
"""

from rich.console import Console
from rich.panel import Panel

from ..config import load_config
from ..ip_pool import get_vm_vxlan_subnet, get_vm_wan_ip
from ..proxmox import get_pool_vms, list_managed_pools, list_vnets_in_zone
from ._helpers import make_connection

console = Console()


def resolve_student(proxmox, config, query: str) -> dict | None:
    """Résout un étudiant par IP WAN, nom de VNet ou nom d'utilisateur.

    Returns:
        Dictionnaire ``{pool_name, vnet_name, vm, wan_ip, vxlan_subnet}``
        ou ``None`` si non trouvé.
    """
    zone = config.openwrt.network.zone_name
    all_vnets = list_vnets_in_zone(proxmox, zone)

    for pool in list_managed_pools(proxmox):
        pool_name = pool["poolid"]

        # Correspondance par nom
        if query.lower() in pool_name.lower():
            vms = get_pool_vms(proxmox, pool_name)
            vm = vms[0] if vms else None
            wan_ip = None
            vxlan = None
            if vm:
                wan_ip = get_vm_wan_ip(proxmox, vm["node"], vm["vmid"])
                vxlan = get_vm_vxlan_subnet(proxmox, vm["node"], vm["vmid"])
            vnet = next(
                (v["vnet"] for v in all_vnets if pool_name in v.get("alias", "")),
                None,
            )
            return {
                "pool_name": pool_name,
                "vnet_name": vnet,
                "vm": vm,
                "wan_ip": wan_ip,
                "vxlan_subnet": vxlan,
            }

        # Correspondance par IP WAN ou VNet
        for vm in get_pool_vms(proxmox, pool_name):
            node, vmid = vm["node"], vm["vmid"]
            wan_ip = get_vm_wan_ip(proxmox, node, vmid)
            vxlan = get_vm_vxlan_subnet(proxmox, node, vmid)

            vnet_name = f"vn{(vmid - config.openwrt.vmid_start):05d}"

            if query == wan_ip or query == vnet_name:
                return {
                    "pool_name": pool_name,
                    "vnet_name": vnet_name,
                    "vm": vm,
                    "wan_ip": wan_ip,
                    "vxlan_subnet": vxlan,
                }

    return None


def cmd_find(args) -> None:
    """Recherche un étudiant par IP WAN, VNet ou nom d'utilisateur."""
    config = load_config()
    proxmox = make_connection()
    query = args.query

    result = resolve_student(proxmox, config, query)
    if not result:
        console.print(f"[yellow]Aucun étudiant trouvé pour la requête : {query}[/yellow]")
        return

    pool = result["pool_name"]
    vnet = result["vnet_name"] or "—"
    wan_ip = result["wan_ip"] or "—"
    vxlan = result["vxlan_subnet"] or "—"
    vm = result.get("vm")

    node = vm.get("node", "—") if vm else "—"
    vmid = str(vm.get("vmid", "—")) if vm else "—"
    status = vm.get("status", "—") if vm else "—"

    content = (
        f"[bold]Pool[/bold]         {pool}\n"
        f"[bold]User Proxmox[/bold]  {pool}@pve\n"
        f"[bold]VNet[/bold]         {vnet}\n"
        f"[bold]IP WAN[/bold]       {wan_ip}\n"
        f"[bold]Subnet VXLAN[/bold] {vxlan}\n"
        f"[bold]VM[/bold]           {vmid}  node={node}  [{status}]"
    )

    console.print(Panel(content, title=f"[bold cyan]{pool}[/bold cyan]", expand=False))

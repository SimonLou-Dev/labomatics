#!/usr/bin/env python3
"""
Gestion du réseau SDN Proxmox : zones VXLAN et VNets.

Un VNet est créé par étudiant dans la zone SDN commune. Le VNet porte :
- un tag VXLAN unique (= student.id)
- un subnet /24 alloué dynamiquement depuis le pool VXLAN
- un alias = student.vnet_alias() (prénom + nom, pour l'affichage Proxmox)

Toute modification SDN (création/suppression de VNet) nécessite un appel
à :func:`apply_sdn` pour être prise en compte par le cluster.
"""

from proxmoxer import ProxmoxAPI


def check_sdn_zone_exists(proxmox: ProxmoxAPI, zone_name: str) -> bool:
    """Vérifie si une zone SDN VXLAN existe dans le cluster."""
    zones = proxmox.cluster.sdn.zones().get()
    return any(
        z for z in zones
        if z.get("type") == "vxlan" and z.get("zone") == zone_name
    )


def list_vnets_in_zone(proxmox: ProxmoxAPI, zone_name: str) -> list[dict]:
    """Liste tous les VNets appartenant à une zone SDN."""
    vnets = proxmox.cluster.sdn.vnets.get()
    return [v for v in vnets if v.get("zone") == zone_name]


def create_vnet(
    proxmox: ProxmoxAPI,
    vnet_name: str,
    zone: str,
    tag: int,
    alias: str = "",
    gateway: str = "",
    subnet: str = "",
) -> None:
    """Crée un VNet dans une zone SDN avec son subnet associé.

    Args:
        vnet_name: Nom du VNet (max 8 caractères, ex. ``"vn00018"``).
        zone: Nom de la zone SDN parente.
        tag: Tag VXLAN (= student.id, unique dans la zone).
        alias: Alias descriptif (student.vnet_alias() = "Jean jdupont").
        gateway: IP de la passerelle du subnet (ex. ``"10.100.18.254"``).
        subnet: Subnet CIDR associé (ex. ``"10.100.18.0/24"``).
    """
    proxmox.cluster.sdn.vnets.post(vnet=vnet_name, zone=zone, tag=tag, alias=alias)
    if subnet:
        proxmox.cluster.sdn.vnets(vnet_name).subnets.post(
            subnet=subnet,
            type="subnet",
            gateway=gateway,
            vnet=vnet_name,
        )


def delete_vnet(proxmox: ProxmoxAPI, vnet_name: str) -> None:
    """Supprime un VNet SDN et tous ses subnets associés."""
    try:
        subnets = proxmox.cluster.sdn.vnets(vnet_name).subnets.get()
        for subnet in subnets:
            proxmox.cluster.sdn.vnets(vnet_name).subnets(subnet["subnet"]).delete()
    except Exception:
        pass
    proxmox.cluster.sdn.vnets(vnet_name).delete()


def apply_sdn(proxmox: ProxmoxAPI) -> None:
    """Applique les changements SDN en attente au cluster."""
    proxmox.cluster.sdn.put()

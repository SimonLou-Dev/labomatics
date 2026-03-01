#!/usr/bin/env python3
"""
Gestion du réseau SDN Proxmox : zones VXLAN et VNets.

L'architecture réseau du lab repose sur une **zone SDN VXLAN** commune
(ex. ``esgilab``) dans laquelle un **VNet** est créé par étudiant.
Chaque VNet porte un tag VXLAN unique (= ``student.id``) et un subnet /24
alloué depuis le pool VXLAN.

Le VNet est lié à son pool étudiant via le champ ``alias``, ce qui permet
de retrouver le VNet lors de la suppression sans stocker d'état externe.

Toute modification SDN (création/suppression de VNet) nécessite un appel
à :func:`apply_sdn` pour être prise en compte par le cluster.
"""

from proxmoxer import ProxmoxAPI


def check_sdn_zone_exists(proxmox: ProxmoxAPI, zone_name: str) -> bool:
    """Vérifie si une zone SDN VXLAN existe dans le cluster.

    Args:
        proxmox: Client API Proxmox authentifié.
        zone_name: Nom de la zone SDN à vérifier.

    Returns:
        ``True`` si la zone existe et est de type ``vxlan``, ``False`` sinon.
    """
    zones = proxmox.cluster.sdn.zones().get()
    return any(
        z for z in zones
        if z.get("type") == "vxlan" and z.get("zone") == zone_name
    )


def list_vnets_in_zone(proxmox: ProxmoxAPI, zone_name: str) -> list[dict]:
    """Liste tous les VNets appartenant à une zone SDN.

    Args:
        proxmox: Client API Proxmox authentifié.
        zone_name: Nom de la zone SDN.

    Returns:
        Liste de dicts VNet ``{vnet, zone, tag, alias, …}``.
    """
    vnets = proxmox.cluster.sdn.vnets.get()
    return [v for v in vnets if v.get("zone") == zone_name]


def create_vnet(
    proxmox: ProxmoxAPI,
    vnet_name: str,
    zone: str,
    tag: int,
    gateway: str = "",
    subnet: str = "",
    alias: str = "",
) -> None:
    """Crée un VNet dans une zone SDN avec son subnet associé.

    Le champ ``alias`` est utilisé pour stocker le nom du pool étudiant
    associé, permettant de retrouver le VNet lors de la suppression.

    Args:
        proxmox: Client API Proxmox authentifié.
        vnet_name: Nom du VNet (max 8 caractères, ex. ``"vn00018"``).
        zone: Nom de la zone SDN parente.
        tag: Tag VXLAN (= ``student.id``, unique dans la zone).
        gateway: IP de la passerelle du subnet (ex. ``"10.100.18.254"``).
        subnet: Subnet CIDR associé (ex. ``"10.100.18.0/24"``).
        alias: Nom du pool étudiant associé (pour retrouver le VNet à la suppression).

    Note:
        Appeler :func:`apply_sdn` après la création pour que le VNet soit effectif.
    """
    proxmox.cluster.sdn.vnets.post(vnet=vnet_name, zone=zone, tag=tag, alias=alias)
    proxmox.cluster.sdn.vnets(vnet_name).subnets.post(
        subnet=subnet,
        type="subnet",
        gateway=gateway,
        vnet=vnet_name,
    )


def delete_vnet(proxmox: ProxmoxAPI, vnet_name: str) -> None:
    """Supprime un VNet SDN et tous ses subnets associés.

    Les subnets doivent être supprimés individuellement avant de supprimer
    le VNet (l'API Proxmox ne fait pas de suppression en cascade).

    Args:
        proxmox: Client API Proxmox authentifié.
        vnet_name: Nom du VNet à supprimer.

    Note:
        Appeler :func:`apply_sdn` après la suppression pour propager les changements.
    """
    subnets = proxmox.cluster.sdn.vnets(vnet_name).subnets.get()
    for subnet in subnets:
        proxmox.cluster.sdn.vnets(vnet_name).subnets(subnet["subnet"]).delete()
    proxmox.cluster.sdn.vnets(vnet_name).delete()


def apply_sdn(proxmox: ProxmoxAPI) -> None:
    """Applique les changements SDN en attente au cluster.

    Doit être appelé après chaque séquence de création/suppression de VNets
    pour que les modifications soient effectivement déployées sur les nœuds.

    Args:
        proxmox: Client API Proxmox authentifié.
    """
    proxmox.cluster.sdn.put()

#!/usr/bin/env python3
"""
Allocation dynamique des IPs WAN et des subnets VXLAN.

La vérité est dans Proxmox : pas de fichier d'état local.

- IPs WAN : lues depuis le champ `ipconfig0` des VMs dans les pools gérés.
- Subnets VXLAN : lus depuis les subnets des VNets SDN existants.

L'allocation retourne la première IP / le premier subnet /24 libre.
"""

from __future__ import annotations

import re
from ipaddress import IPv4Address, IPv4Network
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import InfraConfig


# ── Parsing des exclusions ─────────────────────────────────────────────────────


def _parse_excluded_ips(exclude: list[str]) -> set[IPv4Address]:
    """Parse les règles d'exclusion IP (adresses simples et ranges a.b.c.d-a.b.c.e)."""
    excluded: set[IPv4Address] = set()
    for rule in exclude:
        rule = rule.strip()
        if "-" in rule:
            start_str, end_str = rule.split("-", 1)
            start = int(IPv4Address(start_str.strip()))
            end = int(IPv4Address(end_str.strip()))
            for n in range(start, end + 1):
                excluded.add(IPv4Address(n))
        else:
            try:
                excluded.add(IPv4Address(rule))
            except ValueError:
                pass
    return excluded


def _parse_excluded_networks(exclude: list[str]) -> set[IPv4Network]:
    """Parse les exclusions réseau (CIDR) pour VXLAN."""
    excluded: set[IPv4Network] = set()
    for rule in exclude:
        rule = rule.strip()
        try:
            excluded.add(IPv4Network(rule, strict=False))
        except ValueError:
            pass
    return excluded


# ── WAN ───────────────────────────────────────────────────────────────────────


def get_vm_wan_ip(proxmox, node: str, vmid: int) -> str | None:
    """Extrait l'IP WAN depuis la config cloud-init d'une VM (champ ipconfig0)."""
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()
        ipconfig0 = cfg.get("ipconfig0", "")
        m = re.search(r"ip=(\d+\.\d+\.\d+\.\d+)", ipconfig0)
        return m.group(1) if m else None
    except Exception:
        return None


def get_used_wan_ips(proxmox, config: InfraConfig) -> set[IPv4Address]:
    """Lit les IPs WAN de toutes les VMs dans les pools gérés."""
    from .proxmox import get_pool_vms, list_managed_pools

    used: set[IPv4Address] = set()
    for pool in list_managed_pools(proxmox):
        for vm in get_pool_vms(proxmox, pool["poolid"]):
            ip = get_vm_wan_ip(proxmox, vm["node"], vm["vmid"])
            if ip:
                try:
                    used.add(IPv4Address(ip))
                except ValueError:
                    pass
    return used


def get_available_wan_ips(proxmox, config: InfraConfig) -> list[IPv4Address]:
    """Retourne les IPs WAN disponibles (pool − exclusions − utilisées)."""
    wan = config.openwrt.network.wan_pool
    net = IPv4Network(wan.network, strict=False)
    excluded = _parse_excluded_ips(wan.exclude)
    excluded.add(IPv4Address(wan.gateway))
    excluded.add(net.network_address)
    excluded.add(net.broadcast_address)
    used = get_used_wan_ips(proxmox, config)
    return [a for a in net.hosts() if a not in excluded and a not in used]


def allocate_wan_ip(proxmox, config: InfraConfig) -> str:
    """Alloue la première IP WAN disponible dans le pool."""
    available = get_available_wan_ips(proxmox, config)
    if not available:
        raise ValueError("Pool WAN épuisé — aucune IP disponible")
    return str(available[0])


# ── VXLAN ─────────────────────────────────────────────────────────────────────


def get_vm_vxlan_subnet(proxmox, node: str, vmid: int) -> str | None:
    """Extrait le subnet VXLAN /24 depuis la config cloud-init d'une VM (ipconfig1)."""
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()
        ipconfig1 = cfg.get("ipconfig1", "")
        m = re.search(r"ip=(\d+\.\d+\.\d+)\.\d+/\d+", ipconfig1)
        if m:
            return f"{m.group(1)}.0/24"
        return None
    except Exception:
        return None


def get_used_vxlan_subnets(proxmox, config: InfraConfig) -> set[IPv4Network]:
    """Lit les subnets VXLAN /24 utilisés depuis les VNets SDN."""
    from .proxmox import list_vnets_in_zone

    zone = config.openwrt.network.zone_name
    used: set[IPv4Network] = set()
    try:
        vnets = list_vnets_in_zone(proxmox, zone)
        for vnet in vnets:
            vnet_name = vnet.get("vnet", "")
            try:
                subnets = proxmox.cluster.sdn.vnets(vnet_name).subnets.get()
                for s in subnets:
                    subnet_str = s.get("subnet", "")
                    if subnet_str:
                        used.add(IPv4Network(subnet_str, strict=False))
            except Exception:
                pass
    except Exception:
        pass
    return used


def allocate_vxlan_subnet(proxmox, config: InfraConfig) -> tuple[str, str]:
    """Alloue le premier subnet VXLAN /24 libre.

    Returns:
        Tuple ``(router_ip, subnet_cidr)`` :

        - ``router_ip`` : IP .254 du subnet (gateway OpenWrt)
        - ``subnet_cidr`` : ex. ``"10.100.3.0/24"``
    """
    vxlan_cfg = config.openwrt.network.vxlan_pool
    pool_net = IPv4Network(vxlan_cfg.network, strict=False)
    excluded_nets = _parse_excluded_networks(vxlan_cfg.exclude)
    used = get_used_vxlan_subnets(proxmox, config)

    for subnet in pool_net.subnets(new_prefix=24):
        if subnet in used or subnet in excluded_nets:
            continue
        router_ip = str(subnet.broadcast_address - 1)   # .254
        return router_ip, str(subnet)

    raise ValueError("Pool VXLAN épuisé — aucun subnet /24 disponible")

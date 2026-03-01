#!/usr/bin/env python3
"""
Gestion des pools de ressources Proxmox.

Un **pool** Proxmox regroupe des VMs, des conteneurs LXC et des datastores
pour simplifier la gestion des droits. Ce script crée un pool par étudiant
et y ajoute ses ressources (VM OpenWrt, éventuels LXC).

Les pools créés par ce script sont identifiés par le champ ``comment``
(:data:`POOL_MARKER`) pour ne pas interférer avec les pools créés manuellement.
"""

from proxmoxer import ProxmoxAPI

from .client import POOL_MARKER


def list_managed_pools(proxmox: ProxmoxAPI) -> list[dict]:
    """Liste uniquement les pools créés et gérés par ce script.

    Le filtre s'appuie sur le champ ``comment == POOL_MARKER``.

    Args:
        proxmox: Client API Proxmox authentifié.

    Returns:
        Liste de dicts Proxmox ``{poolid, comment, members, …}``.
    """
    return [p for p in proxmox.pools.get() if p.get("comment") == POOL_MARKER]


def create_pool(proxmox: ProxmoxAPI, pool_name: str) -> None:
    """Crée un pool Proxmox et le marque comme géré par ce script.

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool à créer (généralement le nom de l'étudiant).
    """
    proxmox.pools.post(poolid=pool_name, comment=POOL_MARKER)


def delete_pool(proxmox: ProxmoxAPI, pool_name: str) -> None:
    """Supprime un pool Proxmox.

    Le pool doit être vide (aucun membre) au moment de la suppression,
    sinon l'API Proxmox renvoie une erreur 500.

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool à supprimer.
    """
    proxmox.pools(pool_name).delete()


def add_vm_to_pool(proxmox: ProxmoxAPI, pool_name: str, vmid: int) -> None:
    """Ajoute une VM ou un conteneur LXC à un pool existant.

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool cible.
        vmid: Identifiant de la VM à ajouter.
    """
    proxmox.pools(pool_name).put(vms=str(vmid))


def get_pool_vms(proxmox: ProxmoxAPI, pool_name: str) -> list[dict]:
    """Retourne les membres QEMU (VMs) d'un pool.

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool.

    Returns:
        Liste de dicts membres avec au minimum ``{vmid, name, node, status, type}``.
    """
    pool = proxmox.pools(pool_name).get()
    return [m for m in pool.get("members", []) if m.get("type") == "qemu"]


def get_pool_lxcs(proxmox: ProxmoxAPI, pool_name: str) -> list[dict]:
    """Retourne les membres LXC (conteneurs) d'un pool.

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool.

    Returns:
        Liste de dicts membres avec au minimum ``{vmid, name, node, status, type}``.
    """
    pool = proxmox.pools(pool_name).get()
    return [m for m in pool.get("members", []) if m.get("type") == "lxc"]

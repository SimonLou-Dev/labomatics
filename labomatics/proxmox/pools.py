#!/usr/bin/env python3
"""
Gestion des pools de ressources Proxmox.

Les pools créés par labomatics sont identifiés par le champ ``comment``
(:data:`POOL_MARKER`) pour ne pas interférer avec les pools créés manuellement.
"""

from proxmoxer import ProxmoxAPI

from .client import POOL_MARKER


def list_managed_pools(proxmox: ProxmoxAPI) -> list[dict]:
    """Liste uniquement les pools créés et gérés par labomatics."""
    return [p for p in proxmox.pools.get() if (p.get("comment") or "").startswith(POOL_MARKER)]


def get_pool_vnet_name(pool: dict) -> str | None:
    """Extrait le nom du VNet stocké dans le commentaire du pool (``POOL_MARKER:vnet_name``)."""
    comment = pool.get("comment") or ""
    if ":" in comment:
        return comment.split(":", 1)[1] or None
    return None


def create_pool(proxmox: ProxmoxAPI, pool_name: str, vnet_name: str = "") -> None:
    """Crée un pool Proxmox marqué comme géré par labomatics.

    Le nom du VNet associé est stocké dans le commentaire pour permettre sa suppression ultérieure.
    """
    comment = f"{POOL_MARKER}:{vnet_name}" if vnet_name else POOL_MARKER
    proxmox.pools.post(poolid=pool_name, comment=comment)


def delete_pool(proxmox: ProxmoxAPI, pool_name: str) -> None:
    """Supprime un pool Proxmox (doit être vide)."""
    proxmox.pools(pool_name).delete()


def add_vm_to_pool(proxmox: ProxmoxAPI, pool_name: str, vmid: int) -> None:
    """Ajoute une VM ou un conteneur LXC à un pool existant."""
    proxmox.pools(pool_name).put(vms=str(vmid))


def get_pool_vms(proxmox: ProxmoxAPI, pool_name: str) -> list[dict]:
    """Retourne les membres QEMU (VMs) d'un pool."""
    pool = proxmox.pools(pool_name).get()
    return [m for m in pool.get("members", []) if m.get("type") == "qemu"]


def get_pool_lxcs(proxmox: ProxmoxAPI, pool_name: str) -> list[dict]:
    """Retourne les membres LXC (conteneurs) d'un pool."""
    pool = proxmox.pools(pool_name).get()
    return [m for m in pool.get("members", []) if m.get("type") == "lxc"]

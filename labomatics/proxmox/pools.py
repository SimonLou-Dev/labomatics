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
    return [p for p in proxmox.pools.get() if p.get("comment") == POOL_MARKER]


def create_pool(proxmox: ProxmoxAPI, pool_name: str) -> None:
    """Crée un pool Proxmox marqué comme géré par labomatics."""
    proxmox.pools.post(poolid=pool_name, comment=POOL_MARKER)


def set_pool_limits(
    proxmox: ProxmoxAPI,
    pool_name: str,
    max_cpu: int = 0,
    max_ram_mb: int = 0,
    max_disk_gb: int = 0,
) -> None:
    """Applique les limites de ressources natives Proxmox sur un pool (flavor).

    Proxmox retournera 403 si l'étudiant tente de démarrer une VM dépassant ces limites.
    Les valeurs à 0 sont ignorées (pas de limite).

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool à limiter.
        max_cpu: Nombre max de vCPU cumulés (VMs running).
        max_ram_mb: RAM max en MB cumulée (VMs running).
        max_disk_gb: Disk max en GB cumulé (toutes VMs).
    """
    kwargs: dict = {}
    if max_cpu > 0:
        kwargs["max_cpu"] = max_cpu
    if max_ram_mb > 0:
        kwargs["max_ram"] = max_ram_mb * 1024 * 1024  # Proxmox attend des bytes
    if max_disk_gb > 0:
        kwargs["max_disk"] = max_disk_gb * 1024 * 1024 * 1024
    if kwargs:
        proxmox.pools(pool_name).put(**kwargs)


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

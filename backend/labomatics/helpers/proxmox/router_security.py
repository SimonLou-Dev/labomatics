"""Application de la sécurité réseau d'un routeur étudiant (issue #78).

Logique partagée entre le provisioning (`tasks/lab.py`) et la remédiation
quotidienne (`tasks/security_check.py`) : un seul endroit pour la politique
anti-spoofing WAN, utilisé aussi bien à la création d'un lab que pour migrer
les labs déployés avant ce durcissement.
"""

from __future__ import annotations

from labomatics.helpers.proxmox._root import SYSTEM_POOL_NAME, LabomaticsProxmoxClient


async def apply_router_security(
    proxmox: LabomaticsProxmoxClient,
    *,
    node: str,
    vmid: int,
    user_id: str,
    wan_ip: str,
    current_pool: str | None = None,
) -> None:
    """Met un routeur étudiant en conformité avec la politique de l'issue #78.

    - Déplace la VM du pool étudiant vers le pool système (`current_pool`),
      si elle n'y est pas déjà.
    - Active le firewall de la VM (`enable`, `ipfilter`, `macfilter`).
    - Synchronise l'IPSet `ipfilter-net0` avec l'unique IP WAN autorisée.
    - Donne à l'étudiant un accès `PVEVMUser` direct sur cette VM (sans
      toucher au `PVEVMAdmin` qu'il a par ailleurs sur son propre pool).

    Args:
        proxmox: Client Proxmox déjà connecté au cluster du lab.
        node: Nœud hébergeant la VM.
        vmid: ID de la VM.
        user_id: Identifiant Proxmox de l'étudiant (user@realm).
        wan_ip: IP WAN allouée au routeur (sans préfixe).
        current_pool: Pool Proxmox actuel de la VM si connu et différent du
            pool système — déclenche le déplacement. Omis lors du
            provisioning initial, où le clone cible déjà le pool système.
    """
    if current_pool and current_pool != SYSTEM_POOL_NAME:
        await proxmox.pool.ensure_exists(
            SYSTEM_POOL_NAME,
            comment="Routeurs étudiants + VM plateforme (labomatics)",
        )
        await proxmox.pool.remove_vm(current_pool, vmid)
        await proxmox.pool.add_vm(SYSTEM_POOL_NAME, vmid)

    await proxmox.firewall.set_vm_options(
        node, vmid, enable=True, ipfilter=True, macfilter=True
    )
    await proxmox.firewall.sync_ipset(node, vmid, "ipfilter-net0", [f"{wan_ip}/32"])

    await proxmox.acl.grant_vm_user(vmid, user_id)

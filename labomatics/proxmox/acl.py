#!/usr/bin/env python3
"""
Gestion des utilisateurs et droits d'accès (ACL) Proxmox.

Chaque étudiant dispose d'un compte Proxmox local (realm ``pve``) avec des
droits strictement limités à ses ressources :

+---------------------------------------+------------------+
| Chemin                                | Rôle(s)          |
+=======================================+==================+
| ``/sdn/zones/{zone}/{vnet}``          | PVESDNUser       |
+---------------------------------------+------------------+
| ``/storage``                          | PVEDatastoreUser |
+---------------------------------------+------------------+
| ``/pool/{template_pool}``             | PVETemplateUser  |
|                                       | PVEPoolUser      |
+---------------------------------------+------------------+
| ``/pool/{userpool}``                  | PVETemplateUser  |
|                                       | PVEPoolUser      |
|                                       | PVEVMAdmin       |
+---------------------------------------+------------------+
"""

from typing import TYPE_CHECKING

from proxmoxer import ProxmoxAPI

if TYPE_CHECKING:
    from ..config import InfraConfig
    from ..students import Student


# ── Gestion des utilisateurs ──────────────────────────────────────────────────


def user_exists(proxmox: ProxmoxAPI, userid: str) -> bool:
    """Vérifie si un utilisateur Proxmox existe."""
    try:
        proxmox.access.users(userid).get()
        return True
    except Exception:
        return False


def create_proxmox_user(
    proxmox: ProxmoxAPI,
    userid: str,
    password: str,
    comment: str = "",
) -> None:
    """Crée un utilisateur Proxmox dans le realm local (pve)."""
    proxmox.access.users.post(userid=userid, password=password, comment=comment)


def delete_proxmox_user(proxmox: ProxmoxAPI, userid: str) -> None:
    """Supprime un utilisateur Proxmox."""
    proxmox.access.users(userid).delete()


# ── Gestion des ACL ───────────────────────────────────────────────────────────


def set_acl(
    proxmox: ProxmoxAPI,
    path: str,
    userid: str,
    role: str,
    propagate: int = 0,
) -> None:
    """Ajoute ou met à jour une entrée ACL Proxmox."""
    proxmox.access.acl.put(path=path, users=userid, roles=role, propagate=propagate)


def delete_acl(
    proxmox: ProxmoxAPI,
    path: str,
    userid: str,
    role: str,
) -> None:
    """Supprime une entrée ACL Proxmox."""
    proxmox.access.acl.put(path=path, users=userid, roles=role, delete=1)


# ── ACL par étudiant ──────────────────────────────────────────────────────────


def set_student_acls(
    proxmox: ProxmoxAPI,
    config: "InfraConfig",
    student: "Student",
) -> None:
    """Configure l'ensemble des ACL Proxmox pour un étudiant."""
    userid = student.user_id()
    zone = config.openwrt.network.zone_name
    vnet = student.vnet_name()
    pool = student.pool_name()
    tpl_pool = config.openwrt.template_pool

    set_acl(proxmox, f"/sdn/zones/{zone}/{vnet}", userid, "PVESDNUser")
    set_acl(proxmox, "/storage", userid, "PVEDatastoreUser", propagate=1)
    set_acl(proxmox, f"/pool/{tpl_pool}", userid, "PVETemplateUser")
    set_acl(proxmox, f"/pool/{tpl_pool}", userid, "PVEPoolUser")
    set_acl(proxmox, f"/pool/{pool}", userid, "PVETemplateUser")
    set_acl(proxmox, f"/pool/{pool}", userid, "PVEPoolUser")
    set_acl(proxmox, f"/pool/{pool}", userid, "PVEVMAdmin")


def delete_student_acls(
    proxmox: ProxmoxAPI,
    config: "InfraConfig",
    pool_name: str,
    vnet_name: str | None,
) -> None:
    """Révoque toutes les ACL d'un étudiant."""
    userid = f"{pool_name}@pve"
    zone = config.openwrt.network.zone_name
    tpl_pool = config.openwrt.template_pool

    acls: list[tuple[str, str]] = [
        ("/storage", "PVEDatastoreUser"),
        (f"/pool/{tpl_pool}", "PVETemplateUser"),
        (f"/pool/{tpl_pool}", "PVEPoolUser"),
        (f"/pool/{pool_name}", "PVETemplateUser"),
        (f"/pool/{pool_name}", "PVEPoolUser"),
        (f"/pool/{pool_name}", "PVEVMAdmin"),
    ]
    if vnet_name:
        acls.insert(0, (f"/sdn/zones/{zone}/{vnet_name}", "PVESDNUser"))

    for path, role in acls:
        try:
            delete_acl(proxmox, path, userid, role)
        except Exception:
            pass

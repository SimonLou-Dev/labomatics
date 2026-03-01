#!/usr/bin/env python3
"""
Gestion des utilisateurs et droits d'accès (ACL) Proxmox.

Chaque étudiant dispose d'un compte Proxmox local (realm ``pve``) avec des
droits strictement limités à ses ressources. Les ACL sont définies sur des
chemins spécifiques selon le principe du moindre privilège :

+---------------------------------------+------------------+-------------------------------------+
| Chemin                                | Rôle(s)          | Effet                               |
+=======================================+==================+=====================================+
| ``/sdn/zones/{zone}/{vnet}``          | PVESDNUser       | Accès au VNet VXLAN personnel       |
+---------------------------------------+------------------+-------------------------------------+
| ``/storage``                          | PVEDatastoreUser | Lecture des datastores (disques VM) |
+---------------------------------------+------------------+-------------------------------------+
| ``/pool/{template_pool}``             | PVETemplateUser  | Accès aux templates du lab          |
|                                       | PVEPoolUser      |                                     |
+---------------------------------------+------------------+-------------------------------------+
| ``/pool/{userpool}``                  | PVETemplateUser  | Administration complète de ses VMs  |
|                                       | PVEPoolUser      |                                     |
|                                       | PVEVMAdmin       |                                     |
+---------------------------------------+------------------+-------------------------------------+

Le pool template (configurable via ``template_pool`` dans ``infra.yaml``) est un
pool Proxmox global contenant toutes les templates du lab. Les étudiants y ont
accès en lecture pour pouvoir cloner des VMs supplémentaires.
"""

from typing import TYPE_CHECKING

from proxmoxer import ProxmoxAPI

from .client import POOL_MARKER

if TYPE_CHECKING:
    from ..config import InfraConfig
    from ..students import Student


# ── Gestion des utilisateurs ──────────────────────────────────────────────────


def user_exists(proxmox: ProxmoxAPI, userid: str) -> bool:
    """Vérifie si un utilisateur Proxmox existe.

    Args:
        proxmox: Client API Proxmox authentifié.
        userid: Identifiant complet de l'utilisateur (ex. ``"jdupont@pve"``).

    Returns:
        ``True`` si l'utilisateur existe, ``False`` sinon.
    """
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
    """Crée un utilisateur Proxmox dans le realm local (``pve``).

    Args:
        proxmox: Client API Proxmox authentifié.
        userid: Identifiant complet (ex. ``"jdupont@pve"``).
        password: Mot de passe en clair (hashé côté Proxmox).
        comment: Commentaire optionnel (utilisé pour le marqueur ``POOL_MARKER``).
    """
    proxmox.access.users.post(userid=userid, password=password, comment=comment)


def delete_proxmox_user(proxmox: ProxmoxAPI, userid: str) -> None:
    """Supprime un utilisateur Proxmox.

    Les ACL associées à cet utilisateur subsistent dans Proxmox mais
    deviennent sans effet. Appeler :func:`delete_student_acls` au préalable
    pour un nettoyage complet.

    Args:
        proxmox: Client API Proxmox authentifié.
        userid: Identifiant complet de l'utilisateur (ex. ``"jdupont@pve"``).
    """
    proxmox.access.users(userid).delete()


# ── Gestion des ACL ───────────────────────────────────────────────────────────


def set_acl(
    proxmox: ProxmoxAPI,
    path: str,
    userid: str,
    role: str,
    propagate: int = 0,
) -> None:
    """Ajoute ou met à jour une entrée ACL Proxmox pour un utilisateur.

    Args:
        proxmox: Client API Proxmox authentifié.
        path: Chemin de ressource Proxmox (ex. ``"/pool/jdupont"``).
        userid: Identifiant de l'utilisateur (ex. ``"jdupont@pve"``).
        role: Nom du rôle Proxmox (ex. ``"PVEVMAdmin"``).
        propagate: ``1`` pour propager l'ACL aux ressources enfant, ``0`` sinon.
    """
    proxmox.access.acl.put(path=path, users=userid, roles=role, propagate=propagate)


def delete_acl(
    proxmox: ProxmoxAPI,
    path: str,
    userid: str,
    role: str,
) -> None:
    """Supprime une entrée ACL Proxmox.

    Args:
        proxmox: Client API Proxmox authentifié.
        path: Chemin de ressource Proxmox.
        userid: Identifiant de l'utilisateur.
        role: Nom du rôle à révoquer.
    """
    proxmox.access.acl.put(path=path, users=userid, roles=role, delete=1)


# ── ACL par étudiant ──────────────────────────────────────────────────────────


def set_student_acls(
    proxmox: ProxmoxAPI,
    config: "InfraConfig",
    student: "Student",
) -> None:
    """Configure l'ensemble des ACL Proxmox pour un étudiant.

    Applique les droits définis dans le tableau de la docstring du module
    (SDN, storage, pool template, pool personnel).

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure.
        student: Étudiant pour lequel configurer les droits.
    """
    userid = student.user_id()
    zone = config.openwrt.network.zone_name
    vnet = student.vnet_name()
    pool = student.pool_name()
    tpl_pool = config.openwrt.template_pool

    # Accès au VNet VXLAN personnel de l'étudiant
    set_acl(proxmox, f"/sdn/zones/{zone}/{vnet}", userid, "PVESDNUser")

    # Lecture des datastores (affichage des disques de ses VMs dans l'UI)
    set_acl(proxmox, "/storage", userid, "PVEDatastoreUser", propagate=1)

    # Accès en lecture au pool template global (pour cloner des templates)
    set_acl(proxmox, f"/pool/{tpl_pool}", userid, "PVETemplateUser")
    set_acl(proxmox, f"/pool/{tpl_pool}", userid, "PVEPoolUser")

    # Administration complète du pool personnel (VMs + LXC)
    set_acl(proxmox, f"/pool/{pool}", userid, "PVETemplateUser")
    set_acl(proxmox, f"/pool/{pool}", userid, "PVEPoolUser")
    set_acl(proxmox, f"/pool/{pool}", userid, "PVEVMAdmin")


def delete_student_acls(
    proxmox: ProxmoxAPI,
    config: "InfraConfig",
    pool_name: str,
    vnet_name: str | None,
) -> None:
    """Révoque toutes les ACL d'un étudiant.

    Les erreurs individuelles sont ignorées (ACL déjà absente, etc.)
    pour permettre un nettoyage partiel en cas d'état incohérent.

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure.
        pool_name: Nom du pool étudiant (= nom d'utilisateur).
        vnet_name: Nom du VNet SDN de l'étudiant, ou ``None`` s'il n'existe pas.
    """
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

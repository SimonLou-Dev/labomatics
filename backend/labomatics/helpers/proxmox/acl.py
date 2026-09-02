"""
Client Proxmox pour gérer les ACL (Access Control Lists).

Chaque étudiant dispose d'un compte Proxmox local (realm "pve") avec des
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

from backend.labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxServerError,
    urls,
)


class ProxmoxAclClient:
    """Client pour gérer les ACL Proxmox."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client ACL.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def set(
        self,
        path: str,
        userid: str,
        role: str,
        propagate: int = 0,
    ) -> None:
        """Ajoute ou met à jour une entrée ACL Proxmox.

        Args:
            path: Chemin de la ressource (ex: "/pool/template").
            userid: ID utilisateur au format user@realm.
            role: Rôle à assigner (ex: "PVEVMAdmin").
            propagate: Propagation de l'ACL (0 ou 1).

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(
                    urls.ACCESS_ACL,
                    data={
                        "path": path,
                        "users": userid,
                        "roles": role,
                        "propagate": propagate,
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to set ACL {role} for {userid} on {path}: {e}"
                ) from e

    async def delete(
        self,
        path: str,
        userid: str,
        role: str,
    ) -> None:
        """Supprime une entrée ACL Proxmox.

        Args:
            path: Chemin de la ressource.
            userid: ID utilisateur au format user@realm.
            role: Rôle à révoquer.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(
                    urls.ACCESS_ACL,
                    data={
                        "path": path,
                        "users": userid,
                        "roles": role,
                        "delete": 1,
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to delete ACL {role} for {userid} on {path}: {e}"
                ) from e

    async def set_student(
        self,
        zone: str,
        vnet: str,
        user_pool: str,
        user_id: str,
        template_pool: str = "template",
    ) -> None:
        """Configure toutes les ACL pour un étudiant.

        Args:
            zone: Nom de la zone SDN.
            vnet: Identifiant du VNet de l'étudiant.
            user_pool: Pool de l'utilisateur (ex: "student_name").
            user_id: Identifiant de l'utilisateur user@realm.
            template_pool: Pool des templates (défaut: "template").

        Raises:
            ProxmoxServerError: Problème API.
        """
        acl_configs = [
            (f"/sdn/zones/{zone}/{vnet}", "PVESDNUser", 0),
            ("/storage", "PVEDatastoreUser", 1),
            (f"/pool/{template_pool}", "PVETemplateUser", 0),
            (f"/pool/{template_pool}", "PVEPoolUser", 0),
            (f"/pool/{user_pool}", "PVETemplateUser", 0),
            (f"/pool/{user_pool}", "PVEPoolUser", 0),
            (f"/pool/{user_pool}", "PVEVMAdmin", 0),
        ]

        for path, role, propagate in acl_configs:
            try:
                await self.set(path, user_id, role, propagate)
            except RuntimeError as e:
                raise RuntimeError(
                    f"Failed to configure student ACLs for {user_id}: {e}"
                ) from e

    async def delete_student(
        self,
        user_pool: str,
        zone: str,
        vnet: int,
        user_id: str,
        template_pool: str = "template",
    ) -> None:
        """Révoque toutes les ACL d'un étudiant.

        Args:
            user_pool: Pool de l'utilisateur.
            zone: Nom de la zone SDN.
            vnet: Identifiant du VNet.
            user_id: Identifiant de l'utilisateur user@realm.
            template_pool: Pool des templates (défaut: "template").

        Raises:
            ProxmoxServerError: Problème API.
        """
        acls: list[tuple[str, str]] = [
            ("/storage", "PVEDatastoreUser"),
            (f"/pool/{template_pool}", "PVETemplateUser"),
            (f"/pool/{template_pool}", "PVEPoolUser"),
            (f"/pool/{user_pool}", "PVETemplateUser"),
            (f"/pool/{user_pool}", "PVEPoolUser"),
            (f"/pool/{user_pool}", "PVEVMAdmin"),
        ]
        if vnet:
            acls.insert(0, (f"/sdn/zones/{zone}/{vnet}", "PVESDNUser"))

        for path, role in acls:
            try:
                await self.delete(path, user_id, role)
            except RuntimeError as e:
                raise RuntimeError(
                    f"Failed to revoke student ACLs for {user_id}: {e}"
                ) from e

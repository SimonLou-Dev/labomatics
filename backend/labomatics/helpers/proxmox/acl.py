"""
Client Proxmox pour gérer les ACL, groupes et rôles (Access Control Lists).

Les droits partagés par tous les étudiants (pool système, pool templates,
stockage) sont portés par le groupe `STUDENT_GROUP`, pas répétés par étudiant.
Seuls les chemins propres à chacun restent en ACL individuelle :

+---------------------------------------+------------------+
| Chemin                                | Rôle(s)          |
+=======================================+==================+
| ``/sdn/zones/{zone}/{vnet}``          | PVESDNUser       |
+---------------------------------------+------------------+
| ``/pool/{userpool}``                  | PVEPoolUser      |
|                                       | PVEVMAdmin       |
|                                       | PVETemplateUser  |
+---------------------------------------+------------------+
| ``/vms/{routeur}``                    | STUDENT_VM_ROLE  |
+---------------------------------------+------------------+

Voir `ensure_student_defaults` pour les droits du groupe.
"""

import contextlib

from labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxServerError,
    urls,
)

STUDENT_GROUP = "student"
TEMPLATE_POOL_NAME = "templates"

# Rôle custom pour le routeur étudiant : lecture + console + guest agent,
# explicitement sans VM.PowerMgmt ni droit de config (le routeur est géré par
# le backend, pas par l'étudiant).
STUDENT_VM_ROLE = "LabomaticsVMAudit"
STUDENT_VM_ROLE_PRIVILEGES = (
    "VM.Audit",
    "VM.Console",
    "VM.GuestAgent.Audit",
    "VM.GuestAgent.FileRead",
)


class ProxmoxAclClient:
    """Client pour gérer les ACL, groupes et rôles Proxmox."""

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
        """Ajoute ou met à jour une entrée ACL Proxmox pour un utilisateur.

        Args:
            path: Chemin de la ressource (ex: "/pool/template").
            userid: ID utilisateur au format user@realm.
            role: Rôle à assigner (ex: "PVEVMAdmin").
            propagate: Propagation de l'ACL (0 ou 1).

        Raises:
            RuntimeError: Problème API.
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
        """Supprime une entrée ACL Proxmox pour un utilisateur.

        Args:
            path: Chemin de la ressource.
            userid: ID utilisateur au format user@realm.
            role: Rôle à révoquer.

        Raises:
            RuntimeError: Problème API.
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

    async def set_group_acl(
        self,
        path: str,
        groupid: str,
        role: str,
        propagate: int = 0,
    ) -> None:
        """Ajoute ou met à jour une entrée ACL Proxmox pour un groupe.

        Args:
            path: Chemin de la ressource.
            groupid: Nom du groupe.
            role: Rôle à assigner.
            propagate: Propagation de l'ACL (0 ou 1).

        Raises:
            RuntimeError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(
                    urls.ACCESS_ACL,
                    data={
                        "path": path,
                        "groups": groupid,
                        "roles": role,
                        "propagate": propagate,
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to set ACL {role} for group {groupid} on {path}: {e}"
                ) from e

    async def ensure_role(self, role_id: str, privileges: tuple[str, ...]) -> None:
        """Crée un rôle custom, ou met à jour ses privilèges s'ils ont changé.

        Args:
            role_id: Identifiant du rôle (ex: "LabomaticsVMAudit"). Proxmox
                interdit les rôles custom dont l'ID commence par "PVE"
                (namespace réservé aux rôles intégrés).
            privileges: Privilèges du rôle (ex: ("VM.Audit", "VM.Console")).

        Raises:
            RuntimeError: Problème API.
        """
        privs = ",".join(sorted(privileges))
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.ACCESS_ROLES, cache=False)
                existing = next(
                    (r for r in resp.get("data", []) if r.get("roleid") == role_id),
                    None,
                )
                if existing is None:
                    await client.post(
                        urls.ACCESS_ROLES, data={"roleid": role_id, "privs": privs}
                    )
                else:
                    current = {p for p in (existing.get("privs") or "").split(",") if p}
                    if current != set(privileges):
                        await client.put(
                            urls.access_role(role_id), data={"privs": privs}
                        )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to ensure role {role_id}: {e}") from e

    async def ensure_group(self, group_id: str, comment: str = "") -> None:
        """Crée un groupe Proxmox s'il n'existe pas déjà.

        Args:
            group_id: Nom du groupe.
            comment: Commentaire descriptif.

        Raises:
            RuntimeError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.ACCESS_GROUPS, cache=False)
                exists = any(g.get("groupid") == group_id for g in resp.get("data", []))
                if not exists:
                    await client.post(
                        urls.ACCESS_GROUPS,
                        data={"groupid": group_id, "comment": comment},
                    )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to ensure group {group_id}: {e}") from e

    async def ensure_student_defaults(self, system_pool: str) -> None:
        """Bootstrap idempotent du rôle et du groupe partagés par les étudiants.

        À appeler une fois par cluster (pas par étudiant) : installe le rôle
        `STUDENT_VM_ROLE` et le groupe `STUDENT_GROUP` avec les droits communs
        à tous les étudiants (pool système, pool templates, stockage). Les
        étudiants rejoignent ce groupe via `ProxmoxUserClient.ensure_in_group`.

        Args:
            system_pool: Pool système partagé des routeurs (`SYSTEM_POOL_NAME`).

        Raises:
            RuntimeError: Problème API.
        """
        await self.ensure_role(STUDENT_VM_ROLE, STUDENT_VM_ROLE_PRIVILEGES)
        await self.ensure_group(STUDENT_GROUP, comment="Étudiants Labomatics")

        group_acls = (
            (f"/pool/{system_pool}", "PVEPoolUser"),
            ("/storage/local", "PVEDatastoreAdmin"),
            ("/storage", "PVEDatastoreUser"),
            (f"/pool/{TEMPLATE_POOL_NAME}", "PVEPoolUser"),
            (f"/pool/{TEMPLATE_POOL_NAME}", "PVETemplateUser"),
        )
        for path, role in group_acls:
            await self.set_group_acl(path, STUDENT_GROUP, role, propagate=0)

    async def grant_vm_user(
        self, vmid: int, user_id: str, role: str = STUDENT_VM_ROLE
    ) -> None:
        """Donne à un utilisateur un accès minimal sur une VM précise.

        Utilisé pour le routeur étudiant, placé hors du pool de l'étudiant
        (voir `SYSTEM_POOL_NAME`) : l'accès au pool système lui-même vient du
        groupe `STUDENT_GROUP` (`ensure_student_defaults`), pas d'une ACL
        individuelle.

        Args:
            vmid: ID de la VM.
            user_id: Identifiant de l'utilisateur user@realm.
            role: Rôle à assigner sur la VM (défaut: `STUDENT_VM_ROLE`, lecture
                + console + guest agent, sans droit de modifier sa config).

        Raises:
            RuntimeError: Problème API.
        """
        await self.set(f"/vms/{vmid}", user_id, role, propagate=0)

    async def revoke_vm_user(
        self, vmid: int, user_id: str, role: str = STUDENT_VM_ROLE
    ) -> None:
        """Révoque le rôle donné par `grant_vm_user`.

        Args:
            vmid: ID de la VM.
            user_id: Identifiant de l'utilisateur user@realm.
            role: Rôle à révoquer (doit correspondre à celui donné).

        Raises:
            RuntimeError: Problème API.
        """
        await self.delete(f"/vms/{vmid}", user_id, role)

    async def set_student(
        self,
        zone: str,
        vnet: str,
        user_pool: str,
        user_id: str,
    ) -> None:
        """Configure les ACL propres à un étudiant (supprime avant de réappliquer).

        Les droits communs à tous les étudiants (pool système, templates,
        stockage) sont portés par `STUDENT_GROUP`, pas ici — voir
        `ensure_student_defaults` et `ProxmoxUserClient.ensure_in_group`.

        Args:
            zone: Nom de la zone SDN.
            vnet: Identifiant du VNet de l'étudiant.
            user_pool: Pool de l'utilisateur (ex: "student_name").
            user_id: Identifiant de l'utilisateur user@realm.

        Raises:
            RuntimeError: Problème API.
        """
        # Supprimer les ACL existantes pour éviter les doublons
        with contextlib.suppress(RuntimeError):
            await self.delete_student(user_pool, zone, vnet, user_id)

        acl_configs = (
            (f"/sdn/zones/{zone}/{vnet}", "PVESDNUser"),
            (f"/pool/{user_pool}", "PVEPoolUser"),
            (f"/pool/{user_pool}", "PVEVMAdmin"),
            (f"/pool/{user_pool}", "PVETemplateUser"),
        )

        for path, role in acl_configs:
            try:
                await self.set(path, user_id, role, propagate=0)
            except RuntimeError as e:
                raise RuntimeError(
                    f"Failed to configure student ACLs for {user_id}: {e}"
                ) from e

    async def delete_student(
        self,
        user_pool: str,
        zone: str,
        vnet: str,
        user_id: str,
    ) -> None:
        """Révoque les ACL propres à un étudiant.

        Args:
            user_pool: Pool de l'utilisateur.
            zone: Nom de la zone SDN.
            vnet: Identifiant du VNet.
            user_id: Identifiant de l'utilisateur user@realm.

        Raises:
            RuntimeError: Problème API.
        """
        acls: list[tuple[str, str]] = [
            (f"/pool/{user_pool}", "PVEPoolUser"),
            (f"/pool/{user_pool}", "PVEVMAdmin"),
            (f"/pool/{user_pool}", "PVETemplateUser"),
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

"""Wrapper principal Proxmox avec agrégation de tous les clients."""

from __future__ import annotations

import re
import unicodedata

from labomatics.core.db.models.cluster import Cluster
from labomatics.core.security.crypto import decrypt_secret
from labomatics.helpers.proxmox.acl import STUDENT_GROUP, ProxmoxAclClient
from labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxNotFoundError,
    ProxmoxServerError,
    urls,
)
from labomatics.helpers.proxmox.firewall import ProxmoxVmFirewallClient
from labomatics.helpers.proxmox.pool import ProxmoxPoolClient
from labomatics.helpers.proxmox.sdn import ProxmoxSDNClient
from labomatics.helpers.proxmox.token import ProxmoxTokenClient
from labomatics.helpers.proxmox.user import ProxmoxUserClient
from labomatics.helpers.proxmox.vm import ProxmoxVMClient


def sanitize_pool_name(name: str) -> str:
    """Sanitize pool name for Proxmox (remove accents and special chars)."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9._-]", "", name)


# Pool système partagé : routeurs étudiants + VM plateforme, hors du pool
# personnel de l'étudiant (issue #78 — anti-spoofing / durcissement réseau).
SYSTEM_POOL_NAME = "labomatics-system"


class LabomaticsProxmoxClient:
    """Wrapper principal Proxmox avec tous les sous-clients.

    Crée un pool de connexions réutilisable au cluster et le partage
    avec tous les sous-clients.
    """

    def __init__(self, cluster: Cluster) -> None:
        """Initialise le wrapper Proxmox avec pool partagé.

        Args:
            cluster: Configuration du cluster (doit avoir un credential).

        Raises:
            ValueError: Si le cluster n'a pas de credential configuré.
        """
        self._cluster = cluster

        if not cluster.credential:
            raise ValueError(f"Cluster {cluster.name} has no credential configured")

        cred = cluster.credential
        self._proxmox_client: ProxmoxClientPool = ProxmoxClientPool(
            url=cluster.url,
            user=cred.user,
            token_id=cred.token_id,
            token_secret=cred.encrypted_token_secret,
            decrypt_fn=decrypt_secret,
            ca_cert=cred.ca_cert,
        )

        self.acl = ProxmoxAclClient(proxmox_client=self._proxmox_client)
        self.user = ProxmoxUserClient(proxmox_client=self._proxmox_client)
        self.token = ProxmoxTokenClient(proxmox_client=self._proxmox_client)
        self.pool = ProxmoxPoolClient(proxmox_client=self._proxmox_client)
        self.sdn = ProxmoxSDNClient(proxmox_client=self._proxmox_client)
        self.firewall = ProxmoxVmFirewallClient(proxmox_client=self._proxmox_client)
        self.vm = ProxmoxVMClient(
            proxmox_client=self._proxmox_client, wait_for_task_fn=self._wait_for_task
        )

    async def ensure_student_baseline(self) -> None:
        """Bootstrap idempotent du rôle et du groupe partagés par les étudiants.

        À appeler une fois par cluster (pas par étudiant, voir
        `ProxmoxAclClient.ensure_student_defaults`).

        Raises:
            RuntimeError: Problème API.
        """
        await self.acl.ensure_student_defaults(SYSTEM_POOL_NAME)

    async def create_user_with_deps(
        self,
        user_name: str,
        realm: str,
        zone: str,
        tag: int,
        gateway: str,
        subnet: str,
    ) -> dict:
        """Crée un utilisateur avec toutes les dépendances (token, ACL, VNet).

        Args:
            user_name: Nom d'utilisateur (partie avant @).
            realm: Realm Proxmox (ex: "pve", "ldap").
            zone: Nom de la zone SDN.
            tag: Tag VXLAN (ex: student.id, doit être unique dans la zone).
            gateway: IP de la passerelle du subnet (ex: "10.100.18.254").
            subnet: Subnet CIDR (ex: "10.100.18.0/24").

        Returns:
            Dict avec le token API créé: {"token": (full_id, secret)}.

        Raises:
            RuntimeError: Si une étape échoue (création user, pool, VNet, ACL ou token).
        """
        sanitized_username = sanitize_pool_name(user_name)
        user_id = f"{sanitized_username}@{realm}"
        vnet = f"vn{tag}"

        # 0. Rôle + groupe partagés par les étudiants (idempotent, une fois par
        # cluster suffirait, mais pas cher à revérifier à chaque création)
        await self.ensure_student_baseline()

        # 1. Créer l'utilisateur s'il n'existe pas
        if not await self.user.exists(user_id):
            try:
                await self.user.create(userid=user_id)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to create user: {e}") from e

        # 1b. Rejoindre le groupe étudiant (droits pool système/templates/stockage)
        try:
            await self.user.ensure_in_group(user_id, STUDENT_GROUP)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to add user to student group: {e}") from e

        # 2. S'assurer que le pool existe (créer s'il n'existe pas)
        pool_name = sanitize_pool_name(user_name)
        try:
            await self.pool.ensure_exists(
                pool_name=pool_name, comment=f"Lab pool for {user_name}"
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to ensure pool existence: {e}") from e

        # 3. Créer le vnet s'il n'existe pas
        vnets = await self.sdn.list_vnets_in_zone(zone)
        vnet_exists = any(v.get("vnet") == vnet for v in vnets)

        if not vnet_exists:
            try:
                await self.sdn.create_vnet(
                    vnet_name=vnet,
                    zone=zone,
                    tag=tag,
                    alias=sanitized_username,
                    gateway=gateway,
                    subnet=subnet,
                )
            except RuntimeError as e:
                raise RuntimeError(f"Failed to create VNet: {e}") from e

        # 4. Configurer les ACLs
        try:
            await self.acl.set_student(
                zone=zone, vnet=vnet, user_pool=pool_name, user_id=user_id
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to set student ACLs: {e}") from e

        # 5. Créer le token s'il n'existe pas
        try:
            token = await self.token.create_student(userid=user_id)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to create student token: {e}") from e

        return {"token": token}

    async def _wait_for_task(self, node: str, task_upid: str) -> None:
        """Attend que la tâche Proxmox soit terminée (polling).

        Partagée entre tous les sous-clients (vm, user, sdn, etc.).

        Args:
            node: Nœud hébergeant la tâche.
            task_upid: UPID de la tâche (ex: "1:123:456::...:").

        Raises:
            RuntimeError: Si la tâche a échoué.
        """
        import asyncio

        # Proxmox attend l'UPID complet pour vérifier le statut
        max_retries = 300  # 5 min avec 1s de delay
        for _ in range(max_retries):
            async with self._proxmox_client.get_context_manager() as client:
                try:
                    # Utiliser l'UPID complet comme task_id
                    resp = await client.get(
                        urls.node_task_status(node, task_upid), cache=False
                    )
                    data = resp.get("data", {})
                    status = data.get("status")

                    if status == "stopped":
                        exitstatus = data.get("exitstatus")
                        if exitstatus == "OK":
                            return
                        else:
                            raise RuntimeError(f"Task {task_upid} failed: {exitstatus}")
                except ProxmoxNotFoundError:
                    # Tâche terminée et nettoyée
                    return
                except ProxmoxServerError as e:
                    raise RuntimeError(f"Failed to check task status: {e}") from e

            # Attendre 1s avant le prochain polling
            await asyncio.sleep(1)

        raise RuntimeError(f"Task {task_upid} timeout")

    async def close(self) -> None:
        """Ferme le pool de connexions Proxmox."""
        await self._proxmox_client.close()

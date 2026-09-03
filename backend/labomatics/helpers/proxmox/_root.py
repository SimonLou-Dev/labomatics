"""Wrapper principal Proxmox avec agrégation de tous les clients."""

from __future__ import annotations

from labomatics.core.db.models.cluster import Cluster
from labomatics.core.security.crypto import decrypt_secret
from labomatics.helpers.proxmox.acl import ProxmoxAclClient
from labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxNotFoundError,
    ProxmoxServerError,
    urls,
)
from labomatics.helpers.proxmox.pool import ProxmoxPoolClient
from labomatics.helpers.proxmox.sdn import ProxmoxSDNClient
from labomatics.helpers.proxmox.token import ProxmoxTokenClient
from labomatics.helpers.proxmox.user import ProxmoxUserClient
from labomatics.helpers.proxmox.vm import ProxmoxVMClient


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
        )

        self.acl = ProxmoxAclClient(proxmox_client=self._proxmox_client)
        self.user = ProxmoxUserClient(proxmox_client=self._proxmox_client)
        self.token = ProxmoxTokenClient(proxmox_client=self._proxmox_client)
        self.pool = ProxmoxPoolClient(proxmox_client=self._proxmox_client)
        self.sdn = ProxmoxSDNClient(proxmox_client=self._proxmox_client)
        self.vm = ProxmoxVMClient(
            proxmox_client=self._proxmox_client, wait_for_task_fn=self._wait_for_task
        )

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
        user_id = f"{user_name}@{realm}"
        vnet = f"vn{tag}"

        # 1. Créer l'utilisateur s'il n'existe pas
        if not await self.user.exists(user_id):
            try:
                await self.user.create(userid=user_id)
            except RuntimeError as e:
                raise RuntimeError(f"Failed to create user: {e}") from e

        # 2. Vérifier que le pool existe
        if not await self.pool.exists(user_name):
            raise RuntimeError(f"Pool {user_name} does not exist. Create it manually first.")

        # 3. Créer le vnet s'il n'existe pas
        vnets = await self.sdn.list_vnets_in_zone(zone)
        vnet_exists = any(v.get("vnet") == vnet for v in vnets)

        if not vnet_exists:
            try:
                await self.sdn.create_vnet(
                    vnet_name=vnet,
                    zone=zone,
                    tag=tag,
                    alias=user_name,
                    gateway=gateway,
                    subnet=subnet,
                )
            except RuntimeError as e:
                raise RuntimeError(f"Failed to create VNet: {e}") from e

        # 4. Configurer les ACLs
        try:
            await self.acl.set_student(
                zone=zone, vnet=vnet, user_pool=user_name, user_id=user_id
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

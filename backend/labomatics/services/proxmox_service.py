"""Service pour gérer Proxmox."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from proxmoxer import ProxmoxAPI

from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.security.crypto import decrypt_secret

logger = logging.getLogger(__name__)


class ProxmoxClientWrapper:
    """Wrapper du client Proxmox avec des méthodes custom."""

    def __init__(
        self, cluster_id: UUID, token_id: str, token_secret: str, url: str
    ) -> None:
        self.cluster_id = cluster_id
        self.token_id = token_id
        self.token_secret = token_secret
        self.url = url
        self.proxmox = ProxmoxAPI(
            self.url,
            user=self.token_id,
            token_name="token",
            token_value=self.token_secret,
            verify_ssl=False,
        )

    async def delete_user(self, login: str) -> bool:
        """Supprime un user Proxmox."""
        logger.info(f"Deleting Proxmox user {login}")
        try:
            self.proxmox.access.users(login).delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete Proxmox user {login}: {e}")
            raise


class ProxmoxService:
    """Service pour gérer Proxmox."""

    def __init__(self, cluster_repo: ClusterRepository | None = None) -> None:
        self.cluster_repo = cluster_repo or ClusterRepository()

    async def get_client(self, cluster_id: UUID) -> ProxmoxClientWrapper:
        """Retourne un client Proxmox configuré pour un cluster."""
        cluster = await self.cluster_repo.get(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        credential = cluster.credential
        if not credential:
            raise ValueError(f"No credential found for cluster {cluster_id}")

        token_secret = decrypt_secret(credential.encrypted_token_secret)

        return ProxmoxClientWrapper(
            cluster_id=cluster_id,
            token_id=credential.token_id,
            token_secret=token_secret,
            url=cluster.url,
        )

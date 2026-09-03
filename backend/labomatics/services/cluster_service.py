"""Service pour la gestion des clusters."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm.exc import DetachedInstanceError

from labomatics.api.dto.cluster import (
    ClusterCreateDTO,
    ClusterCredentialWriteDTO,
    ClusterDTO,
    ClusterUpdateDTO,
    RangeRef,
)
from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.models.cluster_credential import ClusterCredential
from labomatics.core.db.models.ip_range_cluster import IpRangeCluster
from labomatics.core.db.models.vxlan_range_cluster import VxlanRangeCluster
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cluster_credential import (
    ClusterCredentialRepository,
)
from labomatics.core.db.repository.ip_range_cluster import IpRangeClusterRepository
from labomatics.core.db.repository.vxlan_range_cluster import (
    VxlanRangeClusterRepository,
)
from labomatics.core.security.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


class ClusterService:
    """Service pour la gestion des clusters Proxmox."""

    def __init__(
        self,
        repo: ClusterRepository | None = None,
        cred_repo: ClusterCredentialRepository | None = None,
        ip_range_cluster_repo: IpRangeClusterRepository | None = None,
        vxlan_range_cluster_repo: VxlanRangeClusterRepository | None = None,
    ) -> None:
        self.repo = repo or ClusterRepository()
        self.cred_repo = cred_repo or ClusterCredentialRepository()
        self.ip_range_cluster_repo = ip_range_cluster_repo or IpRangeClusterRepository()
        self.vxlan_range_cluster_repo = (
            vxlan_range_cluster_repo or VxlanRangeClusterRepository()
        )

    async def list_clusters(self) -> list[ClusterDTO]:
        """Liste tous les clusters."""
        clusters = await self.repo.list()
        return [await self._to_dto(c) for c in clusters]

    async def list_clusters_paginated(self, page: int, per_page: int):
        """Liste les clusters (paginés)."""
        result = await self.repo.paginate(
            filters={},
            page=page,
            per_page=per_page,
            relations=[
                "ip_range_clusters.ip_range",
                "vxlan_range_clusters.vxlan_range",
            ],
        )
        result.items = [await self._to_dto(c) for c in result.items]
        return result

    async def get_cluster(self, cluster_id: UUID) -> ClusterDTO:
        """Récupère un cluster par ID."""
        cluster = await self.repo.get(cluster_id)
        if not cluster:
            raise HTTPException(404, "Cluster not found")
        return await self._to_dto(cluster)

    async def create_cluster(self, dto: ClusterCreateDTO) -> ClusterDTO:
        """Crée un nouveau cluster."""
        cluster = Cluster(
            name=dto.name,
            url=dto.url,
            default_storage=dto.default_storage,
            sdn_zone=dto.sdn_zone,
            wan_bridge=dto.wan_bridge,
            is_active=dto.is_active,
            is_default_for_new_cohorts=dto.is_default_for_new_cohorts,
        )
        cluster = await self.repo.add(cluster)
        return await self._to_dto(cluster)

    async def update_cluster(
        self, cluster_id: UUID, dto: ClusterUpdateDTO
    ) -> ClusterDTO:
        """Met à jour un cluster."""
        values = {}
        if dto.name is not None:
            values["name"] = dto.name
        if dto.url is not None:
            values["url"] = dto.url
        if dto.default_storage is not None:
            values["default_storage"] = dto.default_storage
        if dto.sdn_zone is not None:
            values["sdn_zone"] = dto.sdn_zone
        if dto.wan_bridge is not None:
            values["wan_bridge"] = dto.wan_bridge
        if dto.is_active is not None:
            values["is_active"] = dto.is_active
        if dto.is_default_for_new_cohorts is not None:
            values["is_default_for_new_cohorts"] = dto.is_default_for_new_cohorts

        cluster = await self.repo.update(cluster_id, values)
        return await self._to_dto(cluster)

    async def delete_cluster(self, cluster_id: UUID) -> bool:
        """Supprime un cluster."""
        return await self.repo.delete(cluster_id)

    async def set_default(self, cluster_id: UUID) -> ClusterDTO:
        """Définit le cluster comme défaut pour les nouvelles cohorts."""
        # Retirer le flag par défaut de tous les autres
        all_clusters = await self.repo.list()
        for c in all_clusters:
            if c.is_default_for_new_cohorts:
                await self.repo.update(c.id, {"is_default_for_new_cohorts": False})

        # Ajouter le flag au cluster cible
        cluster = await self.repo.update(
            cluster_id, {"is_default_for_new_cohorts": True}
        )
        return await self._to_dto(cluster)

    async def set_credential(
        self, cluster_id: UUID, dto: ClusterCredentialWriteDTO
    ) -> ClusterDTO:
        """Enregistre les credentials d'authentification Proxmox."""
        # Vérifier que le cluster existe
        cluster = await self.repo.get(cluster_id)
        if not cluster:
            raise HTTPException(404, "Cluster not found")

        # Supprimer l'ancienne credential si elle existe
        existing = await self.cred_repo.get_by_cluster_id(cluster_id)
        if existing:
            await self.cred_repo.delete(existing.id)

        # Créer la nouvelle credential chiffrée
        encrypted_secret = encrypt_secret(dto.token_secret)
        user, token_id = dto.get_user_and_token_id()
        cred = ClusterCredential(
            cluster_id=cluster_id,
            user=user,
            token_id=token_id,
            encrypted_token_secret=encrypted_secret,
            encryption_key_version=1,
        )
        await self.cred_repo.add(cred)

        # Recharger et retourner
        cluster = await self.repo.get(cluster_id)
        if not cluster:
            raise HTTPException(404, "Cluster not found")
        return await self._to_dto(cluster)

    async def attach_ip_range(self, cluster_id: UUID, ip_range_id: UUID) -> None:
        """Attache une plage IP au cluster."""
        # Vérifier que le cluster existe
        cluster = await self.repo.get(cluster_id)
        if not cluster:
            raise HTTPException(404, "Cluster not found")

        # Vérifier que la plage IP existe
        from labomatics.core.db.repository.ip_range import IpRangeRepository

        ip_range_repo = IpRangeRepository()
        ip_range = await ip_range_repo.get(ip_range_id)
        if not ip_range:
            raise HTTPException(404, "IP Range not found")

        # Créer la relation
        rel = IpRangeCluster(ip_range_id=ip_range_id, cluster_id=cluster_id)
        await self.ip_range_cluster_repo.add(rel)

    async def detach_ip_range(self, cluster_id: UUID, ip_range_id: UUID) -> None:
        """Détache une plage IP du cluster."""
        rel = await self.ip_range_cluster_repo.get_by_range_cluster(
            ip_range_id, cluster_id
        )
        if not rel:
            raise HTTPException(404, "IP Range not attached to cluster")

        await self.ip_range_cluster_repo.delete(rel.id)

    async def attach_vxlan_range(self, cluster_id: UUID, vxlan_range_id: UUID) -> None:
        """Attache une plage VXLAN au cluster."""
        # Vérifier que le cluster existe
        cluster = await self.repo.get(cluster_id)
        if not cluster:
            raise HTTPException(404, "Cluster not found")

        # Vérifier que la plage VXLAN existe
        from labomatics.core.db.repository.vxlan_range import VxlanRangeRepository

        vxlan_range_repo = VxlanRangeRepository()
        vxlan_range = await vxlan_range_repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")

        # Créer la relation
        rel = VxlanRangeCluster(vxlan_range_id=vxlan_range_id, cluster_id=cluster_id)
        await self.vxlan_range_cluster_repo.add(rel)

    async def detach_vxlan_range(self, cluster_id: UUID, vxlan_range_id: UUID) -> None:
        """Détache une plage VXLAN du cluster."""
        rel = await self.vxlan_range_cluster_repo.get_by_range_cluster(
            vxlan_range_id, cluster_id
        )
        if not rel:
            raise HTTPException(404, "VXLAN Range not attached to cluster")

        await self.vxlan_range_cluster_repo.delete(rel.id)

    async def test_connection(self, cluster_id: UUID) -> dict:
        """Teste la connexion au cluster Proxmox."""
        cluster = await self.repo.get(cluster_id)
        if not cluster:
            raise HTTPException(404, "Cluster not found")

        # Vérifier que la credential existe
        cred = await self.cred_repo.get_by_cluster_id(cluster_id)
        if not cred:
            raise HTTPException(400, "No credential configured for this cluster")

        try:
            from urllib.parse import urlparse

            from proxmoxer import ProxmoxAPI

            # Déchiffrer le secret
            token_secret = decrypt_secret(cred.encrypted_token_secret)

            # Parser l'URL pour obtenir l'hostname
            parsed = urlparse(cluster.url)
            host = parsed.hostname or parsed.netloc.split(":")[0]
            user, token_name = cred.token_id.split("!")

            # Tester la connexion avec API token
            # Format: user@realm!tokenid:tokensecret
            proxmox = ProxmoxAPI(
                host,
                user=user,
                token_name=token_name,
                token_value=token_secret,
                verify_ssl=False,
            )

            # Effectuer un appel simple pour valider
            nodes = proxmox.nodes.get()
            return {
                "success": True,
                "message": f"Connexion réussie ({len(nodes)} nœuds trouvés)",
                "nodes_count": len(nodes),
            }
        except Exception as e:
            logger.error(f"Failed to connect to cluster {cluster.id}: {e}")
            return {
                "success": False,
                "message": f"Erreur de connexion: {e}",
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    async def _to_dto(self, cluster: Cluster) -> ClusterDTO:
        """Convertit un modèle Cluster en DTO."""
        token_id = None
        has_credential = False
        ip_ranges: list[RangeRef] = []
        vxlan_ranges: list[RangeRef] = []

        # Charger la credential si elle existe
        try:
            cred = await self.cred_repo.get_by_cluster_id(cluster.id)
            if cred:
                has_credential = True
                token_id = cred.token_id
        except Exception as e:
            logger.warning(f"Failed to load credential for cluster {cluster.id}: {e}")

        # Charger les plages avec id et name
        try:
            if cluster.ip_range_clusters:
                ip_ranges = [
                    RangeRef(id=str(rel.ip_range.id), name=rel.ip_range.name)
                    for rel in cluster.ip_range_clusters
                ]
            if cluster.vxlan_range_clusters:
                vxlan_ranges = [
                    RangeRef(id=str(rel.vxlan_range.id), name=rel.vxlan_range.name)
                    for rel in cluster.vxlan_range_clusters
                ]
        except DetachedInstanceError:
            # Relations pas chargées
            pass

        return ClusterDTO(
            id=str(cluster.id),
            name=cluster.name,
            url=cluster.url,
            default_storage=cluster.default_storage,
            sdn_zone=cluster.sdn_zone,
            wan_bridge=cluster.wan_bridge,
            is_active=cluster.is_active,
            is_default_for_new_cohorts=cluster.is_default_for_new_cohorts,
            has_credential=has_credential,
            token_id=token_id,
            ip_ranges=ip_ranges,
            vxlan_ranges=vxlan_ranges,
        )

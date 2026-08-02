"""Service pour la gestion de la configuration globale des clusters."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from labomatics.api.dto.cluster import ClusterCreateDTO, ClusterCredentialWriteDTO
from labomatics.api.dto.cluster_config import (
    ClusterConfigApplyResultDTO,
    ClusterConfigFileDTO,
)
from labomatics.api.dto.ip_range import IpRangeCreateDTO
from labomatics.api.dto.vxlan_range import VxlanRangeCreateDTO
from labomatics.core.config.settings import settings
from labomatics.services.cluster_service import ClusterService
from labomatics.services.ip_range_service import IpRangeService
from labomatics.services.vxlan_range_service import VxlanRangeService

logger = logging.getLogger(__name__)


class ClusterConfigService:
    """Service pour parser et appliquer la configuration des clusters."""

    def __init__(
        self,
        cluster_service: ClusterService | None = None,
        ip_range_service: IpRangeService | None = None,
        vxlan_range_service: VxlanRangeService | None = None,
    ):
        """Initialiser avec les services."""
        self.cluster_service = cluster_service or ClusterService()
        self.ip_range_service = ip_range_service or IpRangeService()
        self.vxlan_range_service = vxlan_range_service or VxlanRangeService()

    async def parse(self, yaml_text: str) -> ClusterConfigFileDTO:
        """Parse un texte YAML en configuration de clusters."""
        try:
            data = yaml.safe_load(yaml_text)
            # Validation basique
            if not isinstance(data, dict) or "clusters" not in data:
                raise ValueError("Invalid cluster config: missing 'clusters' key")

            config = ClusterConfigFileDTO(**data)
            return config
        except Exception as e:
            raise ValueError(f"Failed to parse cluster config: {e}") from e

    async def apply(self, config: ClusterConfigFileDTO) -> ClusterConfigApplyResultDTO:
        """Applique une configuration de clusters (crée/update ranges et clusters)."""
        try:
            # Idempotence: si un cluster existe déjà, skip (bootstrap one-shot)
            for cluster_entry in config.clusters:
                existing = await self.cluster_service.repo.get_by_name(
                    cluster_entry.name
                )
                if existing:
                    logger.info(
                        "Cluster '%s' already exists, skipping bootstrap (idempotent)",
                        cluster_entry.name,
                    )
                    return ClusterConfigApplyResultDTO(
                        success=True,
                        message="Bootstrap skipped: clusters already exist",
                        clusters_processed=0,
                    )
            # 1. Créer/update les IpRange par name
            wan_by_name = {}
            for wan_config in config.wan or []:
                # Chercher si existe déjà
                existing = await self.ip_range_service.repo.get_by_name(wan_config.name)

                if existing:
                    # Update existant
                    dto = await self.ip_range_service.update_ip_range(
                        existing.id,
                        IpRangeCreateDTO(
                            name=wan_config.name,
                            network=wan_config.network,
                            gateway=wan_config.gateway,
                            exclusions=wan_config.exclusions or [],
                        ),
                    )
                else:
                    # Créer nouveau
                    dto = await self.ip_range_service.create_ip_range(
                        IpRangeCreateDTO(
                            name=wan_config.name,
                            network=wan_config.network,
                            gateway=wan_config.gateway,
                            exclusions=wan_config.exclusions or [],
                        )
                    )
                wan_by_name[wan_config.name] = dto

            # 2. Créer/update les VxlanRange par name
            vxlan_by_name = {}
            for vnet_config in config.vnets or []:
                existing = await self.vxlan_range_service.repo.get_by_name(
                    vnet_config.name
                )

                if existing:
                    dto = await self.vxlan_range_service.update_vxlan_range(
                        existing.id,
                        VxlanRangeCreateDTO(
                            name=vnet_config.name,
                            base_network=vnet_config.network,  # YAML: network → DTO: base_network
                            mtu=vnet_config.mtu,
                            vni_min=vnet_config.vni_min,
                            vni_max=vnet_config.vni_max,
                            exclusions=vnet_config.exclusions or [],
                        ),
                    )
                else:
                    dto = await self.vxlan_range_service.create_vxlan_range(
                        VxlanRangeCreateDTO(
                            name=vnet_config.name,
                            base_network=vnet_config.network,  # YAML: network → DTO: base_network
                            mtu=vnet_config.mtu,
                            vni_min=vnet_config.vni_min,
                            vni_max=vnet_config.vni_max,
                            exclusions=vnet_config.exclusions or [],
                        )
                    )
                vxlan_by_name[vnet_config.name] = dto

            # 3. Créer/update les Cluster et attacher ranges
            processed = 0
            for cluster_entry in config.clusters:
                existing_cluster = await self.cluster_service.repo.get_by_name(
                    cluster_entry.name
                )

                if existing_cluster:
                    cluster_dto = await self.cluster_service.update_cluster(
                        existing_cluster.id,
                        ClusterCreateDTO(
                            name=cluster_entry.name,
                            url=cluster_entry.url,
                            default_storage="shared",
                            sdn_zone=cluster_entry.sdn_zone,
                            is_default_for_new_cohorts=True,
                        ),
                    )
                else:
                    cluster_dto = await self.cluster_service.create_cluster(
                        ClusterCreateDTO(
                            name=cluster_entry.name,
                            url=cluster_entry.url,
                            default_storage="shared",
                            sdn_zone=cluster_entry.sdn_zone,
                        )
                    )

                # Attacher WAN ranges
                for wan_cfg in cluster_entry.wan_configs:
                    if wan_cfg.name in wan_by_name:
                        await self.cluster_service.attach_ip_range(
                            cluster_dto.id, wan_by_name[wan_cfg.name].id
                        )

                # Attacher VXLAN range
                if (
                    cluster_entry.vnet_config
                    and cluster_entry.vnet_config.name in vxlan_by_name
                ):
                    await self.cluster_service.attach_vxlan_range(
                        cluster_dto.id, vxlan_by_name[cluster_entry.vnet_config.name].id
                    )

                # Créer/set les credentials si fournis
                if cluster_entry.token_id and cluster_entry.token_secret:
                    await self.cluster_service.set_credential(
                        cluster_dto.id,
                        ClusterCredentialWriteDTO(
                            token_id=cluster_entry.token_id,
                            token_secret=cluster_entry.token_secret,
                        ),
                    )

                processed += 1

            logger.info("Applied cluster config: %d clusters processed", processed)
            return ClusterConfigApplyResultDTO(
                success=True,
                message=f"Applied configuration for {processed} clusters",
                clusters_processed=processed,
            )
        except Exception as e:
            logger.error("Failed to apply cluster config: %s", e, exc_info=True)
            return ClusterConfigApplyResultDTO(
                success=False,
                message=f"Failed to apply configuration: {e}",
                clusters_processed=0,
            )

    async def apply_bootstrap_if_empty(self) -> None:
        """Charge le fichier de config au démarrage s'il existe."""
        config_path = settings.cluster_config_path
        if not config_path:
            logger.info("No CLUSTER_CONFIG_PATH set, skipping bootstrap")
            return

        try:
            path = Path(config_path)
            yaml_text = path.read_text()

            config = await self.parse(yaml_text)
            result = await self.apply(config)
            logger.info("Bootstrap cluster config: %s", result.message)
        except FileNotFoundError:
            logger.warning("CLUSTER_CONFIG_PATH does not exist: %s", config_path)
        except Exception as e:
            logger.error("Failed to bootstrap cluster config: %s", e, exc_info=True)
            raise

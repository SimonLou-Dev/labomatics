"""DTOs pour la configuration globale des clusters."""

from __future__ import annotations

from pydantic import BaseModel


class WanConfigDTO(BaseModel):
    """Configuration WAN d'une plage d'IP."""

    ip_range_id: str | None = None
    name: str


class VnetConfigDTO(BaseModel):
    """Référence VNET (VXLAN) pour un cluster (détails dans la liste vnets globale)."""

    vxlan_range_id: str | None = None
    name: str


class ClusterEntryDTO(BaseModel):
    """Entrée cluster dans la config globale."""

    cluster_id: str | None = None
    name: str
    url: str
    sdn_zone: str
    wan_configs: list[WanConfigDTO]
    vnet_config: VnetConfigDTO | None = None
    token_id: str | None = None
    token_secret: str | None = None


class GlobalWanConfigDTO(BaseModel):
    """Configuration WAN globale."""

    name: str
    network: str
    gateway: str
    exclusions: list[str] | None = None


class GlobalVnetConfigDTO(BaseModel):
    """Configuration VNET globale."""

    name: str
    network: str
    mtu: int = 1350
    vni_min: int = 1000
    vni_max: int = 4000
    exclusions: list[str] | None = None


class ClusterConfigFileDTO(BaseModel):
    """Structure complète du fichier clusterconfig.yaml."""

    clusters: list[ClusterEntryDTO]
    wan: list[GlobalWanConfigDTO] | None = None
    vnets: list[GlobalVnetConfigDTO] | None = None


class ClusterConfigApplyResultDTO(BaseModel):
    """Résultat de l'application d'une configuration."""

    success: bool
    message: str
    clusters_processed: int

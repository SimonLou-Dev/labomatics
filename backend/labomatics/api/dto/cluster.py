"""DTOs pour les clusters Proxmox."""

from __future__ import annotations

from pydantic import BaseModel


class RangeRef(BaseModel):
    """Référence à une plage (ID et nom)."""

    id: str
    name: str


class ClusterCredentialWriteDTO(BaseModel):
    """Credentials à écrire (token + secret)."""

    token_id: str
    token_secret: str


class ClusterDTO(BaseModel):
    """Cluster en lecture (sans token_secret exposé)."""

    id: str
    name: str
    url: str
    default_storage: str
    sdn_zone: str
    wan_bridge: str
    is_active: bool
    is_default_for_new_cohorts: bool
    has_credential: bool
    token_id: str | None = None
    ip_ranges: list[RangeRef] = []
    vxlan_ranges: list[RangeRef] = []


class ClusterCreateDTO(BaseModel):
    """Création d'un cluster."""

    name: str
    url: str
    default_storage: str
    sdn_zone: str
    wan_bridge: str = "vmbr0"
    is_active: bool = True
    is_default_for_new_cohorts: bool = False


class ClusterUpdateDTO(BaseModel):
    """Mise à jour d'un cluster (champs optionnels)."""

    name: str | None = None
    url: str | None = None
    default_storage: str | None = None
    sdn_zone: str | None = None
    wan_bridge: str | None = None
    is_active: bool | None = None
    is_default_for_new_cohorts: bool | None = None

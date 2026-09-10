"""DTOs pour les plages de VNI VXLAN."""

from __future__ import annotations

from pydantic import BaseModel

from labomatics.api.dto.student import StudentSimpleDTO


class VxlanRangeDTO(BaseModel):
    """Plage de VNI VXLAN."""

    id: str
    name: str
    vni_min: int
    vni_max: int
    base_network: str
    mtu: int
    exclusions: list | None = None
    total_vnis: int = 0
    used_count: int = 0
    free_count: int = 0
    utilization_percent: int = 0


class VxlanRangeCreateDTO(BaseModel):
    """Création d'une plage de VNI VXLAN."""

    name: str
    vni_min: int
    vni_max: int
    base_network: str
    mtu: int = 1350
    exclusions: list | None = None


class VxlanRangeUpdateDTO(BaseModel):
    """Mise à jour d'une plage de VNI VXLAN."""

    name: str | None = None
    vni_min: int | None = None
    vni_max: int | None = None
    base_network: str | None = None
    mtu: int | None = None
    exclusions: list | None = None


class VxlanAllocationDTO(BaseModel):
    """Allocation de VNI VXLAN à un étudiant."""

    vni: int | None
    student: StudentSimpleDTO | None
    is_taken: bool


class VxlanAllocationPaginatedDTO(BaseModel):
    """Réponse paginée pour les allocations VXLAN."""

    items: list[VxlanAllocationDTO]
    total: int
    page: int
    per_page: int
    total_pages: int

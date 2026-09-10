"""DTOs pour les plages d'IP WAN."""

from __future__ import annotations

from pydantic import BaseModel

from labomatics.api.dto.student import StudentSimpleDTO


class IpRangeDTO(BaseModel):
    """Plage d'IP WAN."""

    id: str
    name: str
    network: str
    gateway: str
    exclusions: list | None = None
    total_ips: int = 0
    used_count: int = 0
    free_count: int = 0
    utilization_percent: int = 0


class IpRangeCreateDTO(BaseModel):
    """Création d'une plage d'IP WAN."""

    name: str
    network: str
    gateway: str
    exclusions: list | None = None


class IpRangeUpdateDTO(BaseModel):
    """Mise à jour d'une plage d'IP WAN."""

    name: str | None = None
    network: str | None = None
    gateway: str | None = None
    exclusions: list | None = None


class IpAllocationDTO(BaseModel):
    """Allocation d'IP publique à un étudiant."""

    ip_address: str | None
    student: StudentSimpleDTO | None
    is_taken: bool


class IpAllocationPaginatedDTO(BaseModel):
    """Réponse paginée pour les allocations IP."""

    items: list[IpAllocationDTO]
    total: int
    page: int
    per_page: int
    total_pages: int

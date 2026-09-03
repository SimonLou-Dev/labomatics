"""DTOs pour les cohorts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClusterRefDTO(BaseModel):
    """Référence à un cluster dans une cohort."""

    id: str
    name: str
    is_default: bool


class CohortDTO(BaseModel):
    """Cohort avec ses clusters attachés."""

    id: str
    name: str
    year: int
    is_active: bool
    clusters: list[ClusterRefDTO] = []


class CohortListResponseDTO(BaseModel):
    """Réponse paginée de la liste des cohorts."""

    items: list[CohortDTO] = Field(default_factory=list)
    total: int
    page: int
    size: int
    total_pages: int

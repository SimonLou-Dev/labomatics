"""DTOs pour les cohorts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ClusterRefDTO(BaseModel):
    """Référence à un cluster dans une cohort."""

    id: str
    name: str
    is_default: bool
    has_active_lab: bool = False


class CohortDTO(BaseModel):
    """Cohort avec ses clusters attachés."""

    id: str
    name: str
    year: int
    school_year: str
    is_active: bool
    start_date: datetime | None = None
    end_date: datetime | None = None
    clusters: list[ClusterRefDTO] = []


class CohortUpdateDTO(BaseModel):
    """Champs modifiables d'une cohort (dates uniquement)."""

    start_date: datetime | None = None
    end_date: datetime | None = None


class CohortListResponseDTO(BaseModel):
    """Réponse paginée de la liste des cohorts."""

    items: list[CohortDTO] = Field(default_factory=list)
    total_count: int
    page: int
    size: int
    total_pages: int

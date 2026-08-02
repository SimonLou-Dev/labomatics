"""DTO pour les étudiants."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StudentListItemDTO(BaseModel):
    """Étudiant dans la liste."""

    id: str
    login: str
    email: str
    first_name: str
    last_name: str
    cohort_name: str
    wan_ip: str | None = None
    vxlan_tag: int | None = None


class StudentListResponseDTO(BaseModel):
    """Réponse paginée de la liste d'étudiants."""

    items: list[StudentListItemDTO] = Field(default_factory=list)
    total_count: int
    page: int
    size: int
    total_pages: int

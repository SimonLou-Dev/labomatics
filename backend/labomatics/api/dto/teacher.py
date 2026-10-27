"""DTOs pour les professeurs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TeacherCreateDTO(BaseModel):
    """Données de création d'un professeur (via l'UI admin)."""

    first_name: str
    last_name: str
    email: str
    cohort_ids: list[str] = Field(default_factory=list)


class TeacherUpdateDTO(BaseModel):
    """Données de mise à jour d'un professeur."""

    first_name: str
    last_name: str
    email: str
    cohort_ids: list[str] = Field(default_factory=list)


class TeacherListItemDTO(BaseModel):
    """Professeur dans la liste."""

    id: str
    login: str
    email: str
    first_name: str
    last_name: str
    cohort_names: list[str] = Field(default_factory=list)
    is_active: bool


class TeacherListResponseDTO(BaseModel):
    """Réponse paginée de la liste des professeurs."""

    items: list[TeacherListItemDTO] = Field(default_factory=list)
    total_count: int
    page: int
    size: int
    total_pages: int

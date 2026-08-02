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


class StudentImportItemDTO(BaseModel):
    """Élément d'import d'étudiant."""

    id: str
    first_name: str
    last_name: str
    email: str
    cohort_name: str | None = None
    notes: str = ""


class StudentImportDiffDTO(BaseModel):
    """Résultat du diff d'import (preview ou apply)."""

    added: list[StudentImportItemDTO] = Field(default_factory=list)
    modified: list[StudentImportItemDTO] = Field(default_factory=list)
    deleted: list[StudentImportItemDTO] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

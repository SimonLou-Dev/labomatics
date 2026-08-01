"""DTO pour l'import CSV d'étudiants."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StudentImportMappingDTO(BaseModel):
    """Mapping des colonnes CSV vers les champs Student."""

    external_id_column: str
    last_name_column: str
    first_name_column: str
    email_column: str
    cohort_column: str


class StudentImportRowErrorDTO(BaseModel):
    """Erreur de validation d'une ligne CSV."""

    row_index: int
    external_id: str | None = None
    reason: str


class StudentImportCreatedDTO(BaseModel):
    """Étudiant créé lors de l'import."""

    external_id: int
    login: str
    email: str
    cohort_name: str


class StudentImportUpdatedDTO(BaseModel):
    """Étudiant modifié lors de l'import."""

    external_id: int
    changes: dict[str, str]


class StudentImportRemovedDTO(BaseModel):
    """Étudiant supprimé lors de l'import (absent du nouveau CSV)."""

    external_id: int
    login: str


class StudentImportDiffDTO(BaseModel):
    """Résultat du diff ou de l'application de l'import."""

    created: list[StudentImportCreatedDTO] = Field(default_factory=list)
    updated: list[StudentImportUpdatedDTO] = Field(default_factory=list)
    removed: list[StudentImportRemovedDTO] = Field(default_factory=list)
    errors: list[StudentImportRowErrorDTO] = Field(default_factory=list)

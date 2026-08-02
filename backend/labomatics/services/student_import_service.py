"""Service d'import d'étudiants depuis CSV."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from fastapi import HTTPException

from labomatics.api.dto.student import StudentImportDiffDTO, StudentImportItemDTO
from labomatics.core.db.repository.student import StudentRepository


class StudentImportService:
    """Service pour importer des étudiants depuis CSV."""

    def __init__(self, repo: StudentRepository | None = None) -> None:
        self.repo = repo or StudentRepository()

    def parse_csv(
        self, csv_content: bytes, column_mapping: dict[str, str]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Parse le CSV et retourne les données avec les erreurs."""
        try:
            text = csv_content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(400, f"Erreur d'encodage: {e!s}") from e

        try:
            reader = csv.DictReader(StringIO(text))
            if not reader.fieldnames:
                raise HTTPException(400, "Aucun en-tête trouvé dans le CSV")

            data = []
            errors = []

            for idx, row in enumerate(reader, 2):  # 2 car ligne 1 est l'en-tête
                row_data: dict[str, Any] = {}
                for field, column_name in column_mapping.items():
                    if column_name in row:
                        row_data[field] = (row[column_name] or "").strip()
                    else:
                        errors.append(f"Ligne {idx}: colonne '{column_name}' non trouvée")

                # Valider les champs requis
                if row_data.get("id") and row_data.get("email"):
                    data.append(row_data)
                else:
                    errors.append(f"Ligne {idx}: id ou email manquant")

            if not data:
                raise HTTPException(400, "Aucune ligne valide trouvée dans le CSV")

            return data, errors
        except csv.Error as e:
            raise HTTPException(400, f"Erreur lors du parsing CSV: {e!s}") from e

    async def preview_import(
        self, csv_content: bytes, column_mapping: dict[str, str]
    ) -> StudentImportDiffDTO:
        """Fait un preview de l'import (diff) sans modifier la DB. L'ID est utilisé pour le matching."""
        data, parse_errors = self.parse_csv(csv_content, column_mapping)

        # Récupérer les étudiants existants et indexer par external_id (login)
        existing_students = await self.repo.list()
        existing_by_login = {s.login: s for s in existing_students}

        added = []
        modified = []
        deleted = []

        # Parcourir les données du CSV
        for item in data:
            student_id = item.get("id", "")
            if not student_id:
                continue

            if student_id in existing_by_login:
                # Vérifier si modifié
                existing = existing_by_login[student_id]
                if (
                    existing.first_name != item.get("first_name")
                    or existing.last_name != item.get("last_name")
                    or existing.email != item.get("email")
                ):
                    modified.append(
                        StudentImportItemDTO(
                            login=student_id,
                            first_name=item.get("first_name", ""),
                            last_name=item.get("last_name", ""),
                            email=item.get("email", ""),
                            cohort_name=item.get("cohort_name", ""),
                            notes=f"Modifié",
                        )
                    )
            else:
                # Nouveau
                added.append(
                    StudentImportItemDTO(
                        login=student_id,
                        first_name=item.get("first_name", ""),
                        last_name=item.get("last_name", ""),
                        email=item.get("email", ""),
                        cohort_name=item.get("cohort_name", ""),
                        notes="Nouvel étudiant",
                    )
                )

        # Trouver les supprimés (dans DB mais pas dans CSV)
        csv_ids = {item.get("id") for item in data if item.get("id")}
        for login, student in existing_by_login.items():
            if login not in csv_ids:
                deleted.append(
                    StudentImportItemDTO(
                        login=login,
                        first_name=student.first_name,
                        last_name=student.last_name,
                        email=student.email,
                        cohort_name=student.enrollments[0].cohort.name
                        if student.enrollments
                        else "",
                        notes="À supprimer",
                    )
                )

        return StudentImportDiffDTO(
            added=added,
            modified=modified,
            deleted=deleted,
            errors=parse_errors,
        )

    async def apply_import(
        self, csv_content: bytes, column_mapping: dict[str, str]
    ) -> StudentImportDiffDTO:
        """Applique l'import (crée, met à jour, supprime)."""
        preview = await self.preview_import(csv_content, column_mapping)

        # TODO: Implémenter la sauvegarde en DB
        # Pour l'instant, on retourne juste le preview

        return preview

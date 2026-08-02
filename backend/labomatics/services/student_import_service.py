"""Service d'import d'étudiants depuis XML."""

from __future__ import annotations

from typing import Any

import xml.etree.ElementTree as ET
from fastapi import HTTPException

from labomatics.api.dto.student import StudentImportDiffDTO, StudentImportItemDTO
from labomatics.core.db.repository.student import StudentRepository


class StudentImportService:
    """Service pour importer des étudiants depuis XML."""

    def __init__(self, repo: StudentRepository | None = None) -> None:
        self.repo = repo or StudentRepository()

    def parse_xml(
        self, xml_content: bytes, column_mapping: dict[str, str]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Parse le XML et retourne les données avec les erreurs."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise HTTPException(400, f"XML invalide: {e!s}") from e

        rows = root.findall(".//row")
        if not rows:
            raise HTTPException(400, "Aucune ligne trouvée dans le XML")

        data = []
        errors = []

        for idx, row in enumerate(rows, 1):
            row_data: dict[str, Any] = {}
            for field, column_name in column_mapping.items():
                cell = row.find(f".//{column_name}")
                if cell is not None:
                    row_data[field] = (cell.text or "").strip()
                else:
                    errors.append(f"Ligne {idx}: colonne '{column_name}' non trouvée")

            # Valider les champs requis
            if row_data.get("login") and row_data.get("email"):
                data.append(row_data)
            else:
                errors.append(f"Ligne {idx}: login ou email manquant")

        return data, errors

    async def preview_import(
        self, xml_content: bytes, column_mapping: dict[str, str]
    ) -> StudentImportDiffDTO:
        """Fait un preview de l'import (diff) sans modifier la DB."""
        data, parse_errors = self.parse_xml(xml_content, column_mapping)

        # Récupérer les étudiants existants
        existing_students = await self.repo.list()
        existing_by_login = {s.login: s for s in existing_students}

        added = []
        modified = []
        deleted = []

        # Parcourir les données du XML
        for item in data:
            login = item.get("login", "")
            if not login:
                continue

            if login in existing_by_login:
                # Vérifier si modifié
                existing = existing_by_login[login]
                if (
                    existing.first_name != item.get("first_name")
                    or existing.last_name != item.get("last_name")
                    or existing.email != item.get("email")
                ):
                    modified.append(
                        StudentImportItemDTO(
                            login=login,
                            first_name=item.get("first_name", ""),
                            last_name=item.get("last_name", ""),
                            email=item.get("email", ""),
                            cohort_name=item.get("cohort_name", ""),
                            notes=f"Modifié: {existing.email} → {item.get('email')}",
                        )
                    )
            else:
                # Nouveau
                added.append(
                    StudentImportItemDTO(
                        login=login,
                        first_name=item.get("first_name", ""),
                        last_name=item.get("last_name", ""),
                        email=item.get("email", ""),
                        cohort_name=item.get("cohort_name", ""),
                        notes="Nouvel étudiant",
                    )
                )

        # Trouver les supprimés (dans DB mais pas dans XML)
        xml_logins = {item.get("login") for item in data if item.get("login")}
        for login, student in existing_by_login.items():
            if login not in xml_logins:
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
        self, xml_content: bytes, column_mapping: dict[str, str]
    ) -> StudentImportDiffDTO:
        """Applique l'import (crée, met à jour, supprime)."""
        preview = await self.preview_import(xml_content, column_mapping)

        # TODO: Implémenter la sauvegarde en DB
        # Pour l'instant, on retourne juste le preview

        return preview

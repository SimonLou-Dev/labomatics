"""Routes d'import CSV d'étudiants."""

from __future__ import annotations

import csv

from fastapi import APIRouter, File, Form, UploadFile

from labomatics.api.deps.auth import RequireManageUser
from labomatics.api.dto.student_import import (
    StudentImportDiffDTO,
    StudentImportMappingDTO,
)
from labomatics.services import StudentImportServiceDep

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/import/preview")
async def preview_import(
    _user: RequireManageUser,
    service: StudentImportServiceDep,
    file: UploadFile = File(...),
    external_id_column: str = Form(...),
    last_name_column: str = Form(...),
    first_name_column: str = Form(...),
    email_column: str = Form(...),
    cohort_column: str = Form(...),
    year: int = Form(...),
) -> StudentImportDiffDTO:
    """Pré-visualise l'import CSV sans rien modifier."""
    content = await file.read()
    text = content.decode("utf-8")
    rows = list(csv.DictReader(text.splitlines()))

    mapping = StudentImportMappingDTO(
        external_id_column=external_id_column,
        last_name_column=last_name_column,
        first_name_column=first_name_column,
        email_column=email_column,
        cohort_column=cohort_column,
    )

    return await service.preview(rows, mapping, year)


@router.post("/import/apply")
async def apply_import(
    _user: RequireManageUser,
    service: StudentImportServiceDep,
    file: UploadFile = File(...),
    external_id_column: str = Form(...),
    last_name_column: str = Form(...),
    first_name_column: str = Form(...),
    email_column: str = Form(...),
    cohort_column: str = Form(...),
    year: int = Form(...),
) -> StudentImportDiffDTO:
    """Applique l'import CSV (création/modification/suppression d'étudiants)."""
    content = await file.read()
    text = content.decode("utf-8")
    rows = list(csv.DictReader(text.splitlines()))

    mapping = StudentImportMappingDTO(
        external_id_column=external_id_column,
        last_name_column=last_name_column,
        first_name_column=first_name_column,
        email_column=email_column,
        cohort_column=cohort_column,
    )

    return await service.apply(rows, mapping, year)

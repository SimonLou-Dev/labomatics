"""Routes d'import CSV d'étudiants."""

from __future__ import annotations

import csv
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from labomatics.api.deps.auth import CurrentUser, RequireManageUser
from labomatics.api.dto.lab import LabDataDTO
from labomatics.api.dto.student import (
    StudentListResponseDTO,
    StudentImportDiffDTO as StudentImportDiffDTOXML,
)
from labomatics.api.dto.student_import import (
    StudentImportDiffDTO,
    StudentImportMappingDTO,
)
from labomatics.services import StudentImportServiceDep, StudentServiceDep
from labomatics.services.student_import_service import StudentImportService

router = APIRouter(prefix="/students", tags=["students"])


@router.get("")
async def list_students(
    _user: CurrentUser,
    service: StudentServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> StudentListResponseDTO:
    """Liste les étudiants actifs avec pagination."""
    return await service.list_students(page, size)


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


@router.post("/import-xml/preview")
async def preview_import_xml(
    _user: RequireManageUser,
    file: UploadFile = File(...),
    login: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    cohort_name: str = Form(...),
) -> StudentImportDiffDTOXML:
    """Pré-visualise l'import XML sans rien modifier."""
    content = await file.read()
    column_mapping = {
        "login": login,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "cohort_name": cohort_name,
    }
    service = StudentImportService()
    return await service.preview_import(content, column_mapping)


@router.post("/import-xml/apply")
async def apply_import_xml(
    _user: RequireManageUser,
    file: UploadFile = File(...),
    login: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    cohort_name: str = Form(...),
) -> StudentImportDiffDTOXML:
    """Applique l'import XML (création/modification/suppression d'étudiants)."""
    content = await file.read()
    column_mapping = {
        "login": login,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "cohort_name": cohort_name,
    }
    service = StudentImportService()
    return await service.apply_import(content, column_mapping)


@router.get("/me/lab")
async def get_current_lab(
    user: CurrentUser,
    service: StudentServiceDep,
) -> LabDataDTO:
    """Récupère les données du lab du student courant."""
    # Essayer de récupérer le student depuis le subject (keycloak_user_id)
    try:
        keycloak_id = UUID(user.subject)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject invalide",
        ) from e

    student = await service.repo.get_by_keycloak_id(keycloak_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Étudiant non trouvé",
        )

    lab_data = await service.get_lab_data(student.id)
    if not lab_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Données du lab non trouvées",
        )

    return lab_data


@router.get("/{student_id}/lab")
async def get_student_lab(
    user: CurrentUser,
    student_id: str,
    service: StudentServiceDep,
) -> LabDataDTO:
    """Récupère les données du lab d'un étudiant (admin ou l'étudiant lui-même)."""
    try:
        target_id = UUID(student_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID d'étudiant invalide",
        ) from e

    # Vérifier l'authentification: l'user est admin OU c'est son propre lab
    is_admin = "manage_user" in user.roles or "admin" in user.roles
    if not is_admin:
        # Vérifier que c'est le student lui-même
        try:
            current_subject = UUID(user.subject)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé",
            ) from e

        current_student = await service.repo.get_by_keycloak_id(current_subject)
        if not current_student or current_student.id != target_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé",
            )

    # Récupérer les données du lab
    lab_data = await service.get_lab_data(target_id)
    if not lab_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Données du lab non trouvées",
        )

    return lab_data

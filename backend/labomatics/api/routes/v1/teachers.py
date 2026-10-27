"""Endpoints pour les professeurs (#58)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from labomatics.api.deps.auth import RequireManageUser, RequireTeacher
from labomatics.api.dto.student import StudentListResponseDTO
from labomatics.api.dto.teacher import (
    KeycloakUserLookupDTO,
    TeacherCreateDTO,
    TeacherListItemDTO,
    TeacherListResponseDTO,
    TeacherUpdateDTO,
)
from labomatics.services import TeacherServiceDep

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("", response_model=TeacherListResponseDTO)
async def list_teachers(
    _user: RequireManageUser,
    service: TeacherServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> TeacherListResponseDTO:
    """Liste les professeurs (paginé, recherche nom/prénom/email/login)."""
    return await service.list_teachers(page, size, search=search)


@router.get("/lookup-keycloak-user", response_model=KeycloakUserLookupDTO)
async def lookup_keycloak_user(
    _user: RequireManageUser,
    service: TeacherServiceDep,
    login: str = Query(..., min_length=1),
) -> KeycloakUserLookupDTO:
    """Récupère le profil d'un compte Keycloak existant à rattacher comme prof."""
    return await service.lookup_keycloak_user(login)


@router.post("", response_model=TeacherListItemDTO)
async def create_teacher(
    _user: RequireManageUser,
    service: TeacherServiceDep,
    data: TeacherCreateDTO,
) -> TeacherListItemDTO:
    """Crée un professeur (DB + Keycloak + classes assignées + mail)."""
    return await service.create_teacher(data)


@router.patch("/{teacher_id}", response_model=TeacherListItemDTO)
async def update_teacher(
    _user: RequireManageUser,
    service: TeacherServiceDep,
    teacher_id: UUID,
    data: TeacherUpdateDTO,
) -> TeacherListItemDTO:
    """Met à jour le profil et les classes assignées d'un professeur."""
    return await service.update_teacher(teacher_id, data)


@router.delete("/{teacher_id}")
async def delete_teacher(
    _user: RequireManageUser,
    service: TeacherServiceDep,
    teacher_id: UUID,
) -> None:
    """Désactive un professeur (DB + compte Keycloak)."""
    await service.delete_teacher(teacher_id)


@router.get("/me/students", response_model=StudentListResponseDTO)
async def list_my_students(
    user: RequireTeacher,
    service: TeacherServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> StudentListResponseDTO:
    """Recherche parmi les élèves des classes assignées au professeur courant.

    Accessible aussi à un admin (un admin est aussi un prof, #58) : sans
    classe assignée en tant que prof, il verra une page vide ici (il dispose
    déjà de `GET /students`, non scopé, pour voir tous les élèves).
    """
    return await service.list_students_for_teacher(
        UUID(user.subject), page, size, search=search
    )

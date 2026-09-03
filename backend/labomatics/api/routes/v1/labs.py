"""Routes pour la gestion des labs personnels étudiants."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from labomatics.api.deps.auth import CurrentUser
from labomatics.api.dto.lab import LabDataDTO
from labomatics.api.dto.notification import JobDTO
from labomatics.core.db.repository.student import StudentRepository
from labomatics.services import LabServiceDep, StudentServiceDep

router = APIRouter(prefix="/labs", tags=["labs"])


@router.post("", response_model=JobDTO)
async def create_lab(
    user: CurrentUser,
    lab_svc: LabServiceDep,
    cluster_id: UUID | None = Query(None),
) -> JobDTO:
    """Crée un lab pour l'utilisateur courant.

    - Students: cluster_id est optionnel (auto-résolu via enrollment/cohort)
    - Teachers/Admins: cluster_id doit être fourni

    Retourne un JobDTO avec jobId pour suivre la création asynchrone.

    Args:
        user: Utilisateur authentifié (via token Keycloak)
        lab_svc: Service LabService (dépendance injectée)
        cluster_id: ID du cluster Proxmox (optionnel pour students)

    Returns:
        JobDTO contenant le jobId pour suivre l'exécution du job Celery.
    """
    return await lab_svc.create(user=user, cluster_id=cluster_id)


@router.get("/me", response_model=LabDataDTO | None)
async def get_my_lab(
    user: CurrentUser,
    student_svc: StudentServiceDep,
) -> LabDataDTO | None:
    """Récupère les infos du lab courant de l'utilisateur.

    Retourne les détails du lab (IP WAN, VMs, VXLAN tag, lien OpenWRT) si l'utilisateur
    a un lab créé. Retourne None si pas de lab ou pas un student.

    Args:
        user: Utilisateur authentifié (via token Keycloak)
        student_svc: Service StudentService (dépendance injectée)

    Returns:
        LabDataDTO avec les infos du lab, ou None si pas de lab ou pas un student.

    Raises:
        HTTPException 400: Si le subject invalide
    """
    # Chercher le student associé à cet utilisateur Keycloak
    try:
        keycloak_id = UUID(user.subject)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject invalide",
        ) from e

    student_repo = StudentRepository()
    student = await student_repo.get_by_keycloak_id(keycloak_id)

    if not student:
        # L'utilisateur n'est pas un student (teacher/admin)
        return None

    lab_data = await student_svc.get_lab_data(student.id)
    return lab_data

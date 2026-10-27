"""Endpoints pour les cohorts."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from labomatics.api.deps.auth import RequireManageCluster
from labomatics.api.dto.cohort import (
    ClusterRefDTO,
    CohortDTO,
    CohortListResponseDTO,
    CohortUpdateDTO,
)
from labomatics.core.db.models import Cohort, CohortCluster
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.cohort_cluster import CohortClusterRepository
from labomatics.core.db.repository.lab_provisioning import LabProvisioningRepository

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


async def _build_cohort_dto(
    cohort: Cohort,
    cohort_cluster_repo: CohortClusterRepository,
    lab_prov_repo: LabProvisioningRepository,
) -> CohortDTO:
    """Construit le CohortDTO complet (clusters assignés + verrou actif)."""
    cohort_clusters = await cohort_cluster_repo.list_by_cohort(cohort.id)
    clusters = [
        ClusterRefDTO(
            id=str(cc.cluster.id),
            name=cc.cluster.name,
            is_default=cc.is_default,
            has_active_lab=await lab_prov_repo.exists_active_for_cohort_cluster(
                cohort.id, cc.cluster.id
            ),
        )
        for cc in cohort_clusters
    ]
    return CohortDTO(
        id=str(cohort.id),
        name=cohort.name,
        year=cohort.year,
        school_year=f"{cohort.year}-{cohort.year + 1}",
        is_active=cohort.is_active,
        start_date=cohort.start_date,
        end_date=cohort.end_date,
        clusters=clusters,
    )


@router.get("", response_model=CohortListResponseDTO)
async def list_cohorts(
    _user: RequireManageCluster,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> CohortListResponseDTO:
    """Liste les cohorts avec leurs clusters (paginé)."""
    cohort_repo = CohortRepository()
    cohort_cluster_repo = CohortClusterRepository()
    lab_prov_repo = LabProvisioningRepository()

    cohorts = await cohort_repo.list()
    total = len(cohorts)

    # Pagination
    start = (page - 1) * size
    end = start + size
    paginated_cohorts = cohorts[start:end]

    result = [
        await _build_cohort_dto(cohort, cohort_cluster_repo, lab_prov_repo)
        for cohort in paginated_cohorts
    ]

    total_pages = (total + size - 1) // size
    return CohortListResponseDTO(
        items=result,
        total_count=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.patch("/{cohort_id}", response_model=CohortDTO)
async def update_cohort(
    _user: RequireManageCluster,
    cohort_id: UUID,
    data: CohortUpdateDTO,
) -> CohortDTO:
    """Met à jour les dates de début/fin d'une cohort."""
    cohort_repo = CohortRepository()
    cohort_cluster_repo = CohortClusterRepository()
    lab_prov_repo = LabProvisioningRepository()

    cohort = await cohort_repo.get(cohort_id)
    if not cohort:
        raise HTTPException(404, "Cohort not found")

    values = data.model_dump(exclude_unset=True)
    if values:
        cohort = await cohort_repo.update(cohort_id, values)

    return await _build_cohort_dto(cohort, cohort_cluster_repo, lab_prov_repo)


@router.post("/{cohort_id}/clusters/{cluster_id}", response_model=CohortDTO)
async def assign_cluster_to_cohort(
    _user: RequireManageCluster,
    cohort_id: UUID,
    cluster_id: UUID,
) -> CohortDTO:
    """Assigne un cluster à une cohort."""
    cohort_repo = CohortRepository()
    cluster_repo = ClusterRepository()
    cohort_cluster_repo = CohortClusterRepository()
    lab_prov_repo = LabProvisioningRepository()

    cohort = await cohort_repo.get(cohort_id)
    if not cohort:
        raise HTTPException(404, "Cohort not found")

    cluster = await cluster_repo.get(cluster_id)
    if not cluster:
        raise HTTPException(404, "Cluster not found")

    existing = await cohort_cluster_repo.get_by_cohort_cluster(cohort_id, cluster_id)
    if existing:
        raise HTTPException(409, "Cluster already assigned to cohort")

    cc = CohortCluster(cohort_id=cohort_id, cluster_id=cluster_id)
    await cohort_cluster_repo.add(cc)

    return await _build_cohort_dto(cohort, cohort_cluster_repo, lab_prov_repo)


@router.delete("/{cohort_id}/clusters/{cluster_id}")
async def remove_cluster_from_cohort(
    _user: RequireManageCluster,
    cohort_id: UUID,
    cluster_id: UUID,
) -> None:
    """Retire un cluster d'une cohort.

    Bloqué (409) si des étudiants de la cohort ont un lab provisioning/actif
    sur ce cluster, pour ne pas casser leur accès (#53).
    """
    cohort_cluster_repo = CohortClusterRepository()
    lab_prov_repo = LabProvisioningRepository()

    cc = await cohort_cluster_repo.get_by_cohort_cluster(cohort_id, cluster_id)
    if not cc:
        raise HTTPException(404, "Cluster not assigned to cohort")

    if await lab_prov_repo.exists_active_for_cohort_cluster(cohort_id, cluster_id):
        raise HTTPException(
            409,
            "Impossible de retirer ce cluster : des étudiants de cette "
            "promotion y ont un lab actif.",
        )

    await cohort_cluster_repo.delete(cc.id)


@router.patch(
    "/{cohort_id}/clusters/{cluster_id}/set-default", response_model=CohortDTO
)
async def set_default_cluster(
    _user: RequireManageCluster,
    cohort_id: UUID,
    cluster_id: UUID,
) -> CohortDTO:
    """Définit un cluster comme défaut pour une cohort."""
    cohort_repo = CohortRepository()
    cohort_cluster_repo = CohortClusterRepository()
    lab_prov_repo = LabProvisioningRepository()

    cohort = await cohort_repo.get(cohort_id)
    if not cohort:
        raise HTTPException(404, "Cohort not found")

    cc = await cohort_cluster_repo.get_by_cohort_cluster(cohort_id, cluster_id)
    if not cc:
        raise HTTPException(404, "Cluster not assigned to cohort")

    # Unset all other defaults
    all_ccs = await cohort_cluster_repo.list_by_cohort(cohort_id)
    for c in all_ccs:
        if c.is_default:
            await cohort_cluster_repo.update(c.id, {"is_default": False})

    # Set this one as default
    await cohort_cluster_repo.update(cc.id, {"is_default": True})

    return await _build_cohort_dto(cohort, cohort_cluster_repo, lab_prov_repo)

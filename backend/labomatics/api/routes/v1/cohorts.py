"""Endpoints pour les cohorts."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from labomatics.api.dto.cohort import ClusterRefDTO, CohortDTO, CohortListResponseDTO
from labomatics.core.db.models import CohortCluster
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.cohort_cluster import CohortClusterRepository

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


@router.get("", response_model=CohortListResponseDTO)
async def list_cohorts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> CohortListResponseDTO:
    """Liste les cohorts avec leurs clusters (paginé)."""
    cohort_repo = CohortRepository()
    cohort_cluster_repo = CohortClusterRepository()

    cohorts = await cohort_repo.list()
    total = len(cohorts)

    # Pagination
    start = (page - 1) * size
    end = start + size
    paginated_cohorts = cohorts[start:end]

    result = []
    for cohort in paginated_cohorts:
        cohort_clusters = await cohort_cluster_repo.list_by_cohort(cohort.id)
        clusters = [
            ClusterRefDTO(
                id=str(cc.cluster.id),
                name=cc.cluster.name,
                is_default=cc.is_default,
            )
            for cc in cohort_clusters
        ]
        result.append(
            CohortDTO(
                id=str(cohort.id),
                name=cohort.name,
                year=cohort.year,
                is_active=cohort.is_active,
                clusters=clusters,
            )
        )

    total_pages = (total + size - 1) // size
    return CohortListResponseDTO(
        items=result,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post("/{cohort_id}/clusters/{cluster_id}", response_model=CohortDTO)
async def assign_cluster_to_cohort(
    cohort_id: str,
    cluster_id: str,
) -> CohortDTO:
    """Assigne un cluster à une cohort."""
    cohort_repo = CohortRepository()
    cluster_repo = ClusterRepository()
    cohort_cluster_repo = CohortClusterRepository()

    cohort = await cohort_repo.get(UUID(cohort_id))
    if not cohort:
        raise HTTPException(404, "Cohort not found")

    cluster = await cluster_repo.get(UUID(cluster_id))
    if not cluster:
        raise HTTPException(404, "Cluster not found")

    existing = await cohort_cluster_repo.get_by_cohort_cluster(
        UUID(cohort_id), UUID(cluster_id)
    )
    if existing:
        raise HTTPException(409, "Cluster already assigned to cohort")

    cc = CohortCluster(cohort_id=UUID(cohort_id), cluster_id=UUID(cluster_id))
    await cohort_cluster_repo.add(cc)

    cohort_clusters = await cohort_cluster_repo.list_by_cohort(UUID(cohort_id))
    clusters = [
        ClusterRefDTO(
            id=str(c.cluster.id),
            name=c.cluster.name,
            is_default=c.is_default,
        )
        for c in cohort_clusters
    ]
    return CohortDTO(
        id=str(cohort.id),
        name=cohort.name,
        year=cohort.year,
        is_active=cohort.is_active,
        clusters=clusters,
    )


@router.delete("/{cohort_id}/clusters/{cluster_id}")
async def remove_cluster_from_cohort(
    cohort_id: str,
    cluster_id: str,
) -> None:
    """Retire un cluster d'une cohort."""
    cohort_cluster_repo = CohortClusterRepository()

    cc = await cohort_cluster_repo.get_by_cohort_cluster(
        UUID(cohort_id), UUID(cluster_id)
    )
    if not cc:
        raise HTTPException(404, "Cluster not assigned to cohort")

    await cohort_cluster_repo.delete(cc.id)


@router.patch(
    "/{cohort_id}/clusters/{cluster_id}/set-default", response_model=CohortDTO
)
async def set_default_cluster(
    cohort_id: str,
    cluster_id: str,
) -> CohortDTO:
    """Définit un cluster comme défaut pour une cohort."""
    cohort_repo = CohortRepository()
    cohort_cluster_repo = CohortClusterRepository()

    cohort = await cohort_repo.get(UUID(cohort_id))
    if not cohort:
        raise HTTPException(404, "Cohort not found")

    cc = await cohort_cluster_repo.get_by_cohort_cluster(
        UUID(cohort_id), UUID(cluster_id)
    )
    if not cc:
        raise HTTPException(404, "Cluster not assigned to cohort")

    # Unset all other defaults
    all_ccs = await cohort_cluster_repo.list_by_cohort(UUID(cohort_id))
    for c in all_ccs:
        if c.is_default:
            await cohort_cluster_repo.update(c.id, {"is_default": False})

    # Set this one as default
    await cohort_cluster_repo.update(cc.id, {"is_default": True})

    cohort_clusters = await cohort_cluster_repo.list_by_cohort(UUID(cohort_id))
    clusters = [
        ClusterRefDTO(
            id=str(c.cluster.id),
            name=c.cluster.name,
            is_default=c.is_default,
        )
        for c in cohort_clusters
    ]
    return CohortDTO(
        id=str(cohort.id),
        name=cohort.name,
        year=cohort.year,
        is_active=cohort.is_active,
        clusters=clusters,
    )

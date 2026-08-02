"""Routes d'administration des clusters."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from labomatics.api.deps.auth import CurrentUser, RequireManageCluster
from labomatics.api.dto.cluster import (
    ClusterCreateDTO,
    ClusterCredentialWriteDTO,
    ClusterDTO,
    ClusterUpdateDTO,
)
from labomatics.api.dto.pagination import PaginatedDTO
from labomatics.services import ClusterServiceDep

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("")
async def list_clusters(
    _user: CurrentUser,
    service: ClusterServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> PaginatedDTO[ClusterDTO]:
    """Liste tous les clusters (paginée)."""
    return await service.list_clusters_paginated(page, size)


@router.post("")
async def create_cluster(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    dto: ClusterCreateDTO,
) -> ClusterDTO:
    """Crée un nouveau cluster."""
    return await service.create_cluster(dto)


@router.get("/{cluster_id}")
async def get_cluster(
    _user: CurrentUser,
    service: ClusterServiceDep,
    cluster_id: UUID,
) -> ClusterDTO:
    """Récupère les détails d'un cluster."""
    return await service.get_cluster(cluster_id)


@router.patch("/{cluster_id}")
async def update_cluster(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
    dto: ClusterUpdateDTO,
) -> ClusterDTO:
    """Met à jour un cluster."""
    return await service.update_cluster(cluster_id, dto)


@router.delete("/{cluster_id}")
async def delete_cluster(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
) -> None:
    """Supprime un cluster."""
    await service.delete_cluster(cluster_id)


@router.post("/{cluster_id}/set-default")
async def set_default_cluster(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
) -> ClusterDTO:
    """Définit le cluster comme défaut pour les nouvelles cohorts."""
    return await service.set_default(cluster_id)


@router.put("/{cluster_id}/credential")
async def set_cluster_credential(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
    dto: ClusterCredentialWriteDTO,
) -> ClusterDTO:
    """Enregistre les credentials Proxmox pour le cluster."""
    return await service.set_credential(cluster_id, dto)


@router.post("/{cluster_id}/test-connection")
async def test_cluster_connection(
    _user: CurrentUser,
    service: ClusterServiceDep,
    cluster_id: UUID,
) -> dict:
    """Teste la connexion au cluster Proxmox."""
    return await service.test_connection(cluster_id)


@router.post("/{cluster_id}/ip-ranges/{ip_range_id}")
async def attach_ip_range(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
    ip_range_id: UUID,
) -> None:
    """Attache une plage IP au cluster."""
    await service.attach_ip_range(cluster_id, ip_range_id)


@router.delete("/{cluster_id}/ip-ranges/{ip_range_id}")
async def detach_ip_range(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
    ip_range_id: UUID,
) -> None:
    """Détache une plage IP du cluster."""
    await service.detach_ip_range(cluster_id, ip_range_id)


@router.post("/{cluster_id}/vxlan-ranges/{vxlan_range_id}")
async def attach_vxlan_range(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
    vxlan_range_id: UUID,
) -> None:
    """Attache une plage VXLAN au cluster."""
    await service.attach_vxlan_range(cluster_id, vxlan_range_id)


@router.delete("/{cluster_id}/vxlan-ranges/{vxlan_range_id}")
async def detach_vxlan_range(
    _user: RequireManageCluster,
    service: ClusterServiceDep,
    cluster_id: UUID,
    vxlan_range_id: UUID,
) -> None:
    """Détache une plage VXLAN du cluster."""
    await service.detach_vxlan_range(cluster_id, vxlan_range_id)

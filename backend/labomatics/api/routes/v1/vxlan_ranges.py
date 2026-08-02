"""Routes de gestion des plages de VNI VXLAN."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from labomatics.api.deps.auth import CurrentUser, RequireManageCluster
from labomatics.api.dto.pagination import PaginatedDTO
from labomatics.api.dto.vxlan_range import (
    VxlanAllocationDTO,
    VxlanRangeCreateDTO,
    VxlanRangeDTO,
    VxlanRangeUpdateDTO,
)
from labomatics.services import VxlanRangeServiceDep

router = APIRouter(prefix="/vxlan-ranges", tags=["vxlan_ranges"])


@router.get("")
async def list_vxlan_ranges(
    _user: CurrentUser,
    service: VxlanRangeServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> PaginatedDTO[VxlanRangeDTO]:
    """Liste toutes les plages VXLAN (paginée)."""
    return await service.list_vxlan_ranges_paginated(page, size)


@router.post("")
async def create_vxlan_range(
    _user: RequireManageCluster,
    service: VxlanRangeServiceDep,
    dto: VxlanRangeCreateDTO,
) -> VxlanRangeDTO:
    """Crée une nouvelle plage VXLAN."""
    return await service.create_vxlan_range(dto)


@router.patch("/{vxlan_range_id}")
async def update_vxlan_range(
    _user: RequireManageCluster,
    service: VxlanRangeServiceDep,
    vxlan_range_id: UUID,
    dto: VxlanRangeUpdateDTO,
) -> VxlanRangeDTO:
    """Met à jour une plage VXLAN."""
    return await service.update_vxlan_range(vxlan_range_id, dto)


@router.delete("/{vxlan_range_id}")
async def delete_vxlan_range(
    _user: RequireManageCluster,
    service: VxlanRangeServiceDep,
    vxlan_range_id: UUID,
) -> None:
    """Supprime une plage VXLAN."""
    await service.delete_vxlan_range(vxlan_range_id)


@router.get("/{vxlan_range_id}/allocations")
async def get_vxlan_range_allocations(
    _user: CurrentUser,
    service: VxlanRangeServiceDep,
    vxlan_range_id: UUID,
) -> list[VxlanAllocationDTO]:
    """Récupère les allocations VXLAN d'une plage avec infos étudiant."""
    return await service.get_allocations(vxlan_range_id)

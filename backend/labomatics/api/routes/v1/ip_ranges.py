"""Routes de gestion des plages d'IP WAN."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from labomatics.api.deps.auth import CurrentUser, RequireManageCluster
from labomatics.api.dto.ip_range import (
    IpAllocationDTO,
    IpRangeCreateDTO,
    IpRangeDTO,
    IpRangeUpdateDTO,
)
from labomatics.api.dto.pagination import PaginatedDTO
from labomatics.services import IpRangeServiceDep

router = APIRouter(prefix="/ip-ranges", tags=["ip_ranges"])


@router.get("")
async def list_ip_ranges(
    _user: CurrentUser,
    service: IpRangeServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
) -> PaginatedDTO[IpRangeDTO]:
    """Liste toutes les plages d'IP WAN (paginée)."""
    return await service.list_ip_ranges_paginated(page, size)


@router.post("")
async def create_ip_range(
    _user: RequireManageCluster,
    service: IpRangeServiceDep,
    dto: IpRangeCreateDTO,
) -> IpRangeDTO:
    """Crée une nouvelle plage d'IP WAN."""
    return await service.create_ip_range(dto)


@router.patch("/{ip_range_id}")
async def update_ip_range(
    _user: RequireManageCluster,
    service: IpRangeServiceDep,
    ip_range_id: UUID,
    dto: IpRangeUpdateDTO,
) -> IpRangeDTO:
    """Met à jour une plage d'IP WAN."""
    return await service.update_ip_range(ip_range_id, dto)


@router.delete("/{ip_range_id}")
async def delete_ip_range(
    _user: RequireManageCluster,
    service: IpRangeServiceDep,
    ip_range_id: UUID,
) -> None:
    """Supprime une plage d'IP WAN."""
    await service.delete_ip_range(ip_range_id)


@router.get("/{ip_range_id}/allocations")
async def get_ip_range_allocations(
    _user: CurrentUser,
    service: IpRangeServiceDep,
    ip_range_id: UUID,
) -> list[IpAllocationDTO]:
    """Récupère les allocations IP d'une plage avec infos étudiant."""
    return await service.get_allocations(ip_range_id)

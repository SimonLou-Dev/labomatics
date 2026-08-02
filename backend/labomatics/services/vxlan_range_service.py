"""Service pour la gestion des plages de VNI VXLAN."""

from __future__ import annotations

from ipaddress import IPv4Network
from uuid import UUID

from fastapi import HTTPException

from labomatics.api.dto.vxlan_range import (
    VxlanAllocationDTO,
    VxlanRangeCreateDTO,
    VxlanRangeDTO,
    VxlanRangeUpdateDTO,
)
from labomatics.core.db.models.vxlan_allocation import VxlanAllocation
from labomatics.core.db.models.vxlan_range import VxlanRange
from labomatics.core.db.repository.vxlan_allocation import VxlanAllocationRepository
from labomatics.core.db.repository.vxlan_range import VxlanRangeRepository


class VxlanRangeService:
    """Service pour la gestion des plages VNI VXLAN."""

    def __init__(
        self,
        repo: VxlanRangeRepository | None = None,
        alloc_repo: VxlanAllocationRepository | None = None,
    ) -> None:
        self.repo = repo or VxlanRangeRepository()
        self.alloc_repo = alloc_repo or VxlanAllocationRepository()

    async def list_vxlan_ranges(self) -> list[VxlanRangeDTO]:
        """Liste toutes les plages VXLAN."""
        ranges = await self.repo.list()
        return [self._to_dto(r) for r in ranges]

    async def list_vxlan_ranges_paginated(self, page: int, per_page: int):
        """Liste les plages VXLAN (paginées)."""
        result = await self.repo.paginate(filters={}, page=page, per_page=per_page)
        result.items = [self._to_dto(r) for r in result.items]
        return result

    async def get_vxlan_range(self, vxlan_range_id: UUID) -> VxlanRangeDTO:
        """Récupère une plage VXLAN par ID."""
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")
        return self._to_dto(vxlan_range)

    async def create_vxlan_range(self, dto: VxlanRangeCreateDTO) -> VxlanRangeDTO:
        """Crée une nouvelle plage VXLAN."""
        # Normalise le CIDR (PostgreSQL strict: pas de host bits)
        base_net = IPv4Network(dto.base_network, strict=False)

        vxlan_range = VxlanRange(
            name=dto.name,
            vni_min=dto.vni_min,
            vni_max=dto.vni_max,
            base_network=str(base_net),
            mtu=dto.mtu,
            exclusions=dto.exclusions,
        )
        vxlan_range = await self.repo.add(vxlan_range)
        return self._to_dto(vxlan_range)

    async def update_vxlan_range(
        self, vxlan_range_id: UUID, dto: VxlanRangeUpdateDTO
    ) -> VxlanRangeDTO:
        """Met à jour une plage VXLAN."""
        values = {}
        if dto.name is not None:
            values["name"] = dto.name
        if dto.vni_min is not None:
            values["vni_min"] = dto.vni_min
        if dto.vni_max is not None:
            values["vni_max"] = dto.vni_max
        if dto.base_network is not None:
            values["base_network"] = dto.base_network
        if dto.mtu is not None:
            values["mtu"] = dto.mtu
        if dto.exclusions is not None:
            values["exclusions"] = dto.exclusions

        vxlan_range = await self.repo.update(vxlan_range_id, values)
        return self._to_dto(vxlan_range)

    async def delete_vxlan_range(self, vxlan_range_id: UUID) -> bool:
        """Supprime une plage VXLAN."""
        return await self.repo.delete(vxlan_range_id)

    async def get_allocations(self, vxlan_range_id: UUID) -> list[VxlanAllocationDTO]:
        """Récupère toutes les allocations VXLAN d'une plage avec infos étudiant."""
        # Vérifier que la plage existe
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")

        # Récupérer les allocations
        allocations = await self.alloc_repo.list_by_vxlan_range(vxlan_range_id)

        # Convertir en DTOs
        return [self._allocation_to_dto(alloc) for alloc in allocations]

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _to_dto(self, vxlan_range: VxlanRange) -> VxlanRangeDTO:
        """Convertit un modèle VxlanRange en DTO."""
        return VxlanRangeDTO(
            id=str(vxlan_range.id),
            name=vxlan_range.name,
            vni_min=vxlan_range.vni_min,
            vni_max=vxlan_range.vni_max,
            base_network=str(vxlan_range.base_network),
            mtu=vxlan_range.mtu,
            exclusions=vxlan_range.exclusions,
        )

    def _allocation_to_dto(self, allocation: VxlanAllocation) -> VxlanAllocationDTO:
        """Convertit une allocation VXLAN en DTO."""
        student = allocation.student
        return VxlanAllocationDTO(
            vni=allocation.vni,
            student_login=student.login if student else None,
            student_first_name=student.first_name if student else None,
            student_last_name=student.last_name if student else None,
            vxlan_tag_taken_by=student.login if student else None,
            is_taken=student is not None,
        )

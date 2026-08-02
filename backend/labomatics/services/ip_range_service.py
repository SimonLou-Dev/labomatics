"""Service pour la gestion des plages d'IP WAN."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network
from uuid import UUID

from fastapi import HTTPException

from labomatics.api.dto.ip_range import (
    IpAllocationDTO,
    IpRangeCreateDTO,
    IpRangeDTO,
    IpRangeUpdateDTO,
)
from labomatics.core.db.models.ip_allocation import IpAllocation
from labomatics.core.db.models.ip_range import IpRange
from labomatics.core.db.repository.ip_allocation import IpAllocationRepository
from labomatics.core.db.repository.ip_range import IpRangeRepository


class IpRangeService:
    """Service pour la gestion des plages d'IP publiques WAN."""

    def __init__(
        self,
        repo: IpRangeRepository | None = None,
        alloc_repo: IpAllocationRepository | None = None,
    ) -> None:
        self.repo = repo or IpRangeRepository()
        self.alloc_repo = alloc_repo or IpAllocationRepository()

    async def list_ip_ranges(self) -> list[IpRangeDTO]:
        """Liste toutes les plages d'IP."""
        ranges = await self.repo.list()
        return [self._to_dto(r) for r in ranges]

    async def list_ip_ranges_paginated(self, page: int, per_page: int):
        """Liste les plages d'IP (paginées)."""
        result = await self.repo.paginate(filters={}, page=page, per_page=per_page)
        result.items = [self._to_dto(r) for r in result.items]
        return result

    async def get_ip_range(self, ip_range_id: UUID) -> IpRangeDTO:
        """Récupère une plage d'IP par ID."""
        ip_range = await self.repo.get(ip_range_id)
        if not ip_range:
            raise HTTPException(404, "IP Range not found")
        return self._to_dto(ip_range)

    async def create_ip_range(self, dto: IpRangeCreateDTO) -> IpRangeDTO:
        """Crée une nouvelle plage d'IP."""
        # Normalise le CIDR et gateway (PostgreSQL strict)
        network = IPv4Network(dto.network, strict=False)
        gateway = IPv4Address(dto.gateway)

        ip_range = IpRange(
            name=dto.name,
            network=str(network),
            gateway=str(gateway),
            exclusions=dto.exclusions,
        )
        ip_range = await self.repo.add(ip_range)
        return self._to_dto(ip_range)

    async def update_ip_range(
        self, ip_range_id: UUID, dto: IpRangeUpdateDTO
    ) -> IpRangeDTO:
        """Met à jour une plage d'IP."""
        values = {}
        if dto.name is not None:
            values["name"] = dto.name
        if dto.network is not None:
            values["network"] = dto.network
        if dto.gateway is not None:
            values["gateway"] = dto.gateway
        if dto.exclusions is not None:
            values["exclusions"] = dto.exclusions

        ip_range = await self.repo.update(ip_range_id, values)
        return self._to_dto(ip_range)

    async def delete_ip_range(self, ip_range_id: UUID) -> bool:
        """Supprime une plage d'IP."""
        return await self.repo.delete(ip_range_id)

    async def get_allocations(self, ip_range_id: UUID) -> list[IpAllocationDTO]:
        """Récupère toutes les allocations IP d'une plage avec infos étudiant."""
        # Vérifier que la plage existe
        ip_range = await self.repo.get(ip_range_id)
        if not ip_range:
            raise HTTPException(404, "IP Range not found")

        # Récupérer les allocations
        allocations = await self.alloc_repo.list_by_ip_range(ip_range_id)

        # Convertir en DTOs
        return [self._allocation_to_dto(alloc) for alloc in allocations]

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _to_dto(self, ip_range: IpRange) -> IpRangeDTO:
        """Convertit un modèle IpRange en DTO."""
        return IpRangeDTO(
            id=str(ip_range.id),
            name=ip_range.name,
            network=str(ip_range.network),
            gateway=str(ip_range.gateway),
            exclusions=ip_range.exclusions,
        )

    def _allocation_to_dto(self, allocation: IpAllocation) -> IpAllocationDTO:
        """Convertit une allocation IP en DTO."""
        student = allocation.student
        return IpAllocationDTO(
            ip=str(allocation.ip_address),
            student_login=student.login if student else None,
            student_first_name=student.first_name if student else None,
            student_last_name=student.last_name if student else None,
            wan_ip_taken_by=student.login if student else None,
            is_taken=student is not None,
        )

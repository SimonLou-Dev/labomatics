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
        """Liste les plages VXLAN (paginées) avec % d'utilisation."""
        result = await self.repo.paginate(filters={}, page=page, per_page=per_page)
        result.items = [self._to_dto(r) for r in result.items]
        return result

    async def get_vxlan_range(self, vxlan_range_id: UUID) -> VxlanRangeDTO:
        """Récupère une plage VXLAN par ID."""
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")
        allocations = await self.alloc_repo.list_by_vxlan_range(vxlan_range_id)
        return self._to_dto(vxlan_range, used_count=len(allocations))

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

    def _to_dto(self, vxlan_range: VxlanRange, used_count: int = 0) -> VxlanRangeDTO:
        """Convertit un modèle VxlanRange en DTO avec stats d'utilisation."""
        total_vnis = vxlan_range.vni_max - vxlan_range.vni_min + 1
        free_count = max(0, total_vnis - used_count)
        utilization_percent = (
            int((used_count / total_vnis) * 100) if total_vnis > 0 else 0
        )

        return VxlanRangeDTO(
            id=str(vxlan_range.id),
            name=vxlan_range.name,
            vni_min=vxlan_range.vni_min,
            vni_max=vxlan_range.vni_max,
            base_network=str(vxlan_range.base_network),
            mtu=vxlan_range.mtu,
            exclusions=vxlan_range.exclusions,
            total_vnis=total_vnis,
            used_count=used_count,
            free_count=free_count,
            utilization_percent=utilization_percent,
        )

    async def get_first_available_vni(
        self, vxlan_range_id: UUID, cluster_id: UUID | None = None
    ) -> int:
        """
        Récupère le premier VNI disponible d'une plage.

        Args:
            vxlan_range_id: ID de la plage VXLAN
            cluster_id: ID du cluster (optionnel, si None cherche dans tous les clusters)

        Returns:
            Le premier VNI disponible

        Raises:
            HTTPException: Si la plage n'existe pas ou aucun VNI n'est disponible
        """
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")

        if cluster_id:
            range_cluster = await self.range_cluster_repo.get_by_range_cluster(
                vxlan_range_id, cluster_id
            )
            if not range_cluster:
                raise HTTPException(
                    404,
                    f"VXLAN Range {vxlan_range_id} not assigned to cluster "
                    f"{cluster_id}",
                )
            allocations = await self.alloc_repo.list_by_cluster(cluster_id)
        else:
            allocations = await self.alloc_repo.list_by_vxlan_range(vxlan_range_id)

        used_vnis = {alloc.vni for alloc in allocations}

        exclusions = vxlan_range.exclusions or []
        excluded_vnis = set(exclusions) if exclusions else set()

        for vni in range(vxlan_range.vni_min, vxlan_range.vni_max + 1):
            if vni not in used_vnis and vni not in excluded_vnis:
                return vni

        raise HTTPException(409, f"No available VNI in range {vxlan_range.name}")

    async def get_first_available_vnis(
        self, vxlan_range_id: UUID, count: int, cluster_id: UUID | None = None
    ) -> list[int]:
        """
        Récupère les N premiers VNIs disponibles d'une plage.

        Args:
            vxlan_range_id: ID de la plage VXLAN
            count: Nombre de VNIs à obtenir
            cluster_id: ID du cluster (optionnel)

        Returns:
            Liste des N premiers VNIs disponibles

        Raises:
            HTTPException: Si pas assez de VNIs disponibles
        """
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")

        if cluster_id:
            range_cluster = await self.range_cluster_repo.get_by_range_cluster(
                vxlan_range_id, cluster_id
            )
            if not range_cluster:
                raise HTTPException(
                    404,
                    f"VXLAN Range {vxlan_range_id} not assigned to cluster "
                    f"{cluster_id}",
                )
            allocations = await self.alloc_repo.list_by_cluster(cluster_id)
        else:
            allocations = await self.alloc_repo.list_by_vxlan_range(vxlan_range_id)

        used_vnis = {alloc.vni for alloc in allocations}

        exclusions = vxlan_range.exclusions or []
        excluded_vnis = set(exclusions) if exclusions else set()

        available = []
        for vni in range(vxlan_range.vni_min, vxlan_range.vni_max + 1):
            if vni not in used_vnis and vni not in excluded_vnis:
                available.append(vni)
                if len(available) == count:
                    break

        if len(available) < count:
            raise HTTPException(
                409,
                f"Not enough available VNIs in range {vxlan_range.name} "
                f"(need {count}, found {len(available)})",
            )

        return available

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

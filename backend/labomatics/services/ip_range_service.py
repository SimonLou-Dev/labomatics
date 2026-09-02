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
        """Liste les plages d'IP (paginées) avec % d'utilisation."""
        result = await self.repo.paginate(filters={}, page=page, per_page=per_page)
        result.items = [self._to_dto(r) for r in result.items]
        return result

    async def get_ip_range(self, ip_range_id: UUID) -> IpRangeDTO:
        """Récupère une plage d'IP par ID."""
        ip_range = await self.repo.get(ip_range_id)
        if not ip_range:
            raise HTTPException(404, "IP Range not found")
        allocations = await self.alloc_repo.list_by_ip_range(ip_range_id)
        return self._to_dto(ip_range, used_count=len(allocations))

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

    def _to_dto(self, ip_range: IpRange, used_count: int = 0) -> IpRangeDTO:
        """Convertit un modèle IpRange en DTO avec stats d'utilisation."""
        network = IPv4Network(ip_range.network, strict=False)
        total_ips = max(1, network.num_addresses - 2)  # Exclude network and broadcast
        free_count = max(0, total_ips - used_count)
        utilization_percent = (
            int((used_count / total_ips) * 100) if total_ips > 0 else 0
        )

        return IpRangeDTO(
            id=str(ip_range.id),
            name=ip_range.name,
            network=str(ip_range.network),
            gateway=str(ip_range.gateway),
            exclusions=ip_range.exclusions,
            total_ips=total_ips,
            used_count=used_count,
            free_count=free_count,
            utilization_percent=utilization_percent,
        )

    async def get_first_available_ip(
        self, ip_range_id: UUID, cluster_id: UUID | None = None
    ) -> IPv4Address:
        """
        Récupère la première IP WAN disponible d'une plage.

        Args:
            ip_range_id: ID de la plage IP
            cluster_id: ID du cluster (optionnel, si None cherche dans tous les clusters)

        Returns:
            La première IPv4Address disponible

        Raises:
            HTTPException: Si la plage n'existe pas ou aucune IP n'est disponible
        """

        ip_range = await self.repo.get(ip_range_id)
        if not ip_range:
            raise HTTPException(404, "IP Range not found")

        network = IPv4Network(ip_range.network, strict=False)
        usable_addresses = list(network.hosts())

        if cluster_id:
            from labomatics.core.db.repository.ip_range_cluster import (
                IpRangeClusterRepository,
            )

            range_cluster_repo = IpRangeClusterRepository()
            range_cluster = await range_cluster_repo.get_by_range_cluster(
                ip_range_id, cluster_id
            )
            if not range_cluster:
                raise HTTPException(
                    404,
                    f"IP Range {ip_range_id} not assigned to cluster {cluster_id}",
                )
            allocations = await self.alloc_repo.list_by_cluster(cluster_id)
        else:
            allocations = await self.alloc_repo.list_by_ip_range(ip_range_id)

        used_addresses = {IPv4Address(str(alloc.ip_address)) for alloc in allocations}

        exclusions = ip_range.exclusions or []
        excluded_addresses = {IPv4Address(ex) for ex in exclusions}

        for addr in usable_addresses:
            if addr not in used_addresses and addr not in excluded_addresses:
                return addr

        raise HTTPException(409, f"No available IP addresses in range {ip_range.name}")

    async def get_first_available_ips(
        self, ip_range_id: UUID, count: int, cluster_id: UUID | None = None
    ) -> list[IPv4Address]:
        """
        Récupère les N premières IPs WAN disponibles d'une plage.

        Args:
            ip_range_id: ID de la plage IP
            count: Nombre d'IPs à obtenir
            cluster_id: ID du cluster (optionnel)

        Returns:
            Liste des N premières IPv4Address disponibles

        Raises:
            HTTPException: Si pas assez d'IPs disponibles
        """
        ip_range = await self.repo.get(ip_range_id)
        if not ip_range:
            raise HTTPException(404, "IP Range not found")

        network = IPv4Network(ip_range.network, strict=False)
        usable_addresses = list(network.hosts())

        if cluster_id:
            from labomatics.core.db.repository.ip_range_cluster import (
                IpRangeClusterRepository,
            )

            range_cluster_repo = IpRangeClusterRepository()
            range_cluster = await range_cluster_repo.get_by_range_cluster(
                ip_range_id, cluster_id
            )
            if not range_cluster:
                raise HTTPException(
                    404,
                    f"IP Range {ip_range_id} not assigned to cluster {cluster_id}",
                )
            allocations = await self.alloc_repo.list_by_cluster(cluster_id)
        else:
            allocations = await self.alloc_repo.list_by_ip_range(ip_range_id)

        used_addresses = {IPv4Address(str(alloc.ip_address)) for alloc in allocations}

        exclusions = ip_range.exclusions or []
        excluded_addresses = {IPv4Address(ex) for ex in exclusions}

        available = []
        for addr in usable_addresses:
            if addr not in used_addresses and addr not in excluded_addresses:
                available.append(addr)
                if len(available) == count:
                    break

        if len(available) < count:
            raise HTTPException(
                409,
                f"Not enough available IP addresses in range {ip_range.name} "
                f"(need {count}, found {len(available)})",
            )

        return available

    def _allocation_to_dto(self, allocation: IpAllocation) -> IpAllocationDTO:
        """Convertit une allocation IP en DTO."""
        student = allocation.student
        return IpAllocationDTO(
            ip_address=str(allocation.ip_address),
            student_login=student.login if student else None,
            student_first_name=student.first_name if student else None,
            student_last_name=student.last_name if student else None,
            wan_ip_taken_by=student.login if student else None,
            is_taken=student is not None,
        )

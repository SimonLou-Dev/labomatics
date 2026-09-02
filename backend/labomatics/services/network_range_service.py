"""Service pour la gestion des ranges réseau VXLAN."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network
from uuid import UUID

from fastapi import HTTPException

from labomatics.core.db.repository.vxlan_allocation import (
    VxlanAllocationRepository,
)
from labomatics.core.db.repository.vxlan_range import VxlanRangeRepository
from labomatics.core.db.repository.vxlan_range_cluster import (
    VxlanRangeClusterRepository,
)


class NetworkRangeService:
    """Service pour la gestion des ranges réseau VXLAN."""

    def __init__(
        self,
        repo: VxlanRangeRepository | None = None,
        alloc_repo: VxlanAllocationRepository | None = None,
        range_cluster_repo: VxlanRangeClusterRepository | None = None,
    ) -> None:
        self.repo = repo or VxlanRangeRepository()
        self.alloc_repo = alloc_repo or VxlanAllocationRepository()
        self.range_cluster_repo = range_cluster_repo or VxlanRangeClusterRepository()

    async def get_first_available_network_range(
        self, vxlan_range_id: UUID, cluster_id: UUID | None = None
    ) -> IPv4Network:
        """
        Récupère la première range réseau VXLAN disponible d'une plage.

        La range réseau est calculée à partir du VNI associé :
        pour chaque VNI utilisé, on génère un subnet en incrémentant l'octet d'ordre élevé.

        Args:
            vxlan_range_id: ID de la plage VXLAN
            cluster_id: ID du cluster (optionnel, si None cherche dans tous les clusters)

        Returns:
            La première IPv4Network disponible

        Raises:
            HTTPException: Si la plage n'existe pas ou aucune range n'est disponible
        """
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")

        base_network = IPv4Network(vxlan_range.base_network, strict=False)

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
                subnet = self._calculate_subnet(base_network, vni)
                return subnet

        raise HTTPException(
            409, f"No available network ranges in VXLAN range {vxlan_range.name}"
        )

    async def get_first_available_network_ranges(
        self, vxlan_range_id: UUID, count: int, cluster_id: UUID | None = None
    ) -> list[IPv4Network]:
        """
        Récupère les N premières ranges réseau VXLAN disponibles d'une plage.

        Args:
            vxlan_range_id: ID de la plage VXLAN
            count: Nombre de ranges à obtenir
            cluster_id: ID du cluster (optionnel)

        Returns:
            Liste des N premières IPv4Network disponibles

        Raises:
            HTTPException: Si pas assez de ranges disponibles
        """
        vxlan_range = await self.repo.get(vxlan_range_id)
        if not vxlan_range:
            raise HTTPException(404, "VXLAN Range not found")

        base_network = IPv4Network(vxlan_range.base_network, strict=False)

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
                subnet = self._calculate_subnet(base_network, vni)
                available.append(subnet)
                if len(available) == count:
                    break

        if len(available) < count:
            raise HTTPException(
                409,
                f"Not enough available network ranges in VXLAN range "
                f"{vxlan_range.name} (need {count}, found {len(available)})",
            )

        return available

    @staticmethod
    def _calculate_subnet(base_network: IPv4Network, vni: int) -> IPv4Network:
        """
        Calcule le subnet VXLAN pour un VNI donné.

        La logique par défaut incrémente l'octet d'ordre élevé du base_network
        par le VNI. Cette implémentation supporte les networks /16 et supérieurs.

        Example: base_network=10.0.0.0/16, vni=100 -> 10.100.0.0/24

        Args:
            base_network: Le network de base
            vni: Le VNI à utiliser

        Returns:
            Le subnet calculé

        Raises:
            ValueError: Si le VNI est trop grand pour le prefixlen
        """
        base_ip = base_network.network_address
        octets = bytearray(base_ip.packed)

        if base_network.prefixlen <= 8:
            octets[1] = vni & 0xFF
            new_ip = IPv4Address(bytes(octets))
            prefixlen = 24
        elif base_network.prefixlen <= 16:
            octets[2] = vni & 0xFF
            new_ip = IPv4Address(bytes(octets))
            prefixlen = 24
        else:
            octets[3] = vni & 0xFF
            new_ip = IPv4Address(bytes(octets))
            prefixlen = 25

        return IPv4Network(f"{new_ip}/{prefixlen}", strict=False)

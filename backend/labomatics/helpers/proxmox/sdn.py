"""Client Proxmox pour gérer les réseaux SDN."""

from backend.labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxServerError,
    urls,
)


class ProxmoxSDNClient:
    """Client pour gérer les zones et réseaux VXLAN Proxmox."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client SDN.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def check_zone_exists(self, zone_name: str) -> bool:
        """Vérifie si une zone SDN VXLAN existe.

        Args:
            zone_name: Nom de la zone SDN.

        Returns:
            True si la zone VXLAN existe, False sinon.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.SDN_ZONES, cache=True)
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch SDN zones: {e}") from e

        zones = resp.get("data", [])
        return any(
            z for z in zones if z.get("type") == "vxlan" and z.get("zone") == zone_name
        )

    async def list_vnets_in_zone(self, zone_name: str) -> list[dict]:
        """Liste tous les VNets d'une zone SDN.

        Args:
            zone_name: Nom de la zone SDN.

        Returns:
            Liste des VNets appartenant à la zone.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.SDN_VNETS, cache=True)
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch VNets for zone {zone_name}: {e}"
                ) from e

        vnets = resp.get("data", [])
        return [v for v in vnets if v.get("zone") == zone_name]

    async def create_vnet(
        self,
        vnet_name: str,
        zone: str,
        tag: int,
        alias: str = "",
        gateway: str = "",
        subnet: str = "",
    ) -> None:
        """Crée un VNet dans une zone SDN avec son subnet optionnel.

        Args:
            vnet_name: Nom du VNet (max 8 caractères, ex: "vn00018").
            zone: Nom de la zone SDN parente.
            tag: Tag VXLAN (unique dans la zone, ex: student.id).
            alias: Alias descriptif optionnel.
            gateway: IP de la passerelle du subnet (ex: "10.100.18.254").
            subnet: Subnet CIDR associé (ex: "10.100.18.0/24").

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.post(
                    urls.SDN_VNETS,
                    data={
                        "vnet": vnet_name,
                        "zone": zone,
                        "tag": tag,
                        "alias": alias,
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to create VNet {vnet_name} in zone {zone}: {e}"
                ) from e

            if subnet:
                try:
                    await client.post(
                        urls.sdn_vnet_subnets(vnet_name),
                        data={
                            "subnet": subnet,
                            "type": "subnet",
                            "gateway": gateway,
                            "vnet": vnet_name,
                        },
                    )
                except ProxmoxServerError as e:
                    raise RuntimeError(
                        f"Failed to create subnet {subnet} for VNet {vnet_name}: {e}"
                    ) from e

    async def delete_vnet(self, vnet_name: str) -> None:
        """Supprime un VNet et tous ses subnets associés.

        Args:
            vnet_name: Nom du VNet.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.sdn_vnet_subnets(vnet_name))
                subnets = resp.get("data", [])
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch subnets for VNet {vnet_name}: {e}"
                ) from e

            for subnet in subnets:
                subnet_name = subnet.get("subnet")
                try:
                    await client.delete(urls.sdn_vnet_subnet(vnet_name, subnet_name))
                except ProxmoxServerError as e:
                    raise RuntimeError(
                        f"Failed to delete subnet {subnet_name} from VNet {vnet_name}: {e}"
                    ) from e

            try:
                await client.delete(urls.sdn_vnet(vnet_name))
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to delete VNet {vnet_name}: {e}") from e

    async def apply(self) -> None:
        """Applique les changements SDN en attente au cluster.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(urls.SDN)
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to apply SDN changes: {e}") from e

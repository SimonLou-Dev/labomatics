"""Client Proxmox pour gérer les VMs QEMU."""

import re

from backend.labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxNotFoundError,
    ProxmoxServerError,
    urls,
)


class ProxmoxVMClient:
    """Client Proxmox pour gérer les VMs QEMU et conteneurs."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client VM.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def pick_node(self) -> str:
        """Sélectionne le nœud avec le plus de mémoire disponible.

        Returns:
            Nom du nœud Proxmox ayant le plus de RAM libre.

        Raises:
            RuntimeError: Si aucun nœud n'est en ligne.
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.NODES, cache=True)
                nodes = resp.get("data", [])
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch nodes list: {e}") from e

        online = [n for n in nodes if n.get("status") == "online"]
        if not online:
            raise RuntimeError("No online Proxmox nodes available in cluster")

        return str(
            max(online, key=lambda n: n.get("maxmem", 0) - n.get("mem", 0))["node"]
        )

    async def local_node(self, host: str) -> str:
        """Retourne le nœud correspondant à l'hôte de connexion.

        Args:
            host: Hostname ou FQDN du nœud.

        Returns:
            Nom du nœud Proxmox correspondant.

        Raises:
            RuntimeError: Si aucun nœud n'est en ligne.
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.NODES, cache=True)
                nodes = [n for n in resp.get("data", []) if n.get("status") == "online"]
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch nodes list: {e}") from e

        short = host.split(".")[0]
        for n in nodes:
            if n["node"] == host or n["node"] == short:
                return str(n["node"])

        return await self.pick_node()

    async def exists(self, vmid: int) -> bool:
        """Vérifie si une VM ou un conteneur existe.

        Args:
            vmid: ID de la VM/LXC.

        Returns:
            True si la VM existe, False sinon.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.CLUSTER_RESOURCES, params={"type": "vm"}, cache=True
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch cluster resources: {e}") from e

        resources = resp.get("data", [])
        return any(int(r.get("vmid", -1)) == vmid for r in resources)

    async def find_node(self, vmid: int) -> str | None:
        """Trouve le nœud hébergeant une VM donnée.

        Args:
            vmid: ID de la VM.

        Returns:
            Nom du nœud ou None si VM non trouvée.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.CLUSTER_RESOURCES, params={"type": "vm"}, cache=True
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch cluster resources: {e}") from e

        resources = resp.get("data", [])
        for r in resources:
            if int(r.get("vmid", -1)) == vmid:
                node = r.get("node")
                return str(node) if node is not None else None
        return None

    async def get_wan_ip(self, node: str, vmid: int) -> str | None:
        """Extrait l'IP WAN de la config cloud-init (ipconfig0).

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.

        Returns:
            Adresse IP WAN ou None si non trouvée/introuvable.

        Raises:
            ProxmoxNotFoundError: VM non trouvée.
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.qemu_config(node, vmid), cache=True)
            except ProxmoxNotFoundError as e:
                raise ProxmoxNotFoundError(f"VM {vmid} not found on node {node}") from e
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch VM {vmid} config on node {node}: {e}"
                ) from e

        config = resp.get("data", {})
        ipconfig0 = config.get("ipconfig0", "")

        m = re.search(r"ip=(\d+\.\d+\.\d+\.\d+)", ipconfig0)
        return m.group(1) if m else None

    async def get_vxlan_subnet(self, node: str, vmid: int) -> str | None:
        """Extrait le subnet VXLAN /24 de la config cloud-init (ipconfig1).

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.

        Returns:
            Subnet CIDR /24 ou None si non trouvé/introuvable.

        Raises:
            ProxmoxNotFoundError: VM non trouvée.
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.qemu_config(node, vmid), cache=True)
            except ProxmoxNotFoundError as e:
                raise ProxmoxNotFoundError(f"VM {vmid} not found on node {node}") from e
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch VM {vmid} config on node {node}: {e}"
                ) from e

        config = resp.get("data", {})
        ipconfig1 = config.get("ipconfig1", "")

        m = re.search(r"ip=(\d+\.\d+\.\d+)\.\d+/\d+", ipconfig1)
        if m:
            return f"{m.group(1)}.0/24"
        return None

    async def get_description(self, node: str, vmid: int) -> str:
        """Retourne la description (notes) d'une VM.

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.

        Returns:
            Description de la VM (chaîne vide si absente).

        Raises:
            ProxmoxNotFoundError: VM non trouvée.
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.qemu_config(node, vmid), cache=True)
            except ProxmoxNotFoundError as e:
                raise ProxmoxNotFoundError(f"VM {vmid} not found on node {node}") from e
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch VM {vmid} config on node {node}: {e}"
                ) from e

        config = resp.get("data", {})
        return str(config.get("description", ""))

    @staticmethod
    def get_disk_size_gb(config: dict) -> int:
        """Calcule la taille totale des disques en GB.

        Args:
            config: Configuration Proxmox de la VM contenant scsi*, virtio*, ide*, sata*.

        Returns:
            Taille totale des disques en GB.

        Raises:
            KeyError: Si la structure du config est invalide.
        """

        total = 0
        size_pattern = re.compile(r"size=(\d+(?:\.\d+)?)([GMKT]?)", re.IGNORECASE)
        disk_keys = {k for k in config if re.match(r"^(scsi|virtio|ide|sata)\d+$", k)}
        for key in disk_keys:
            val = str(config.get(key, ""))
            m = size_pattern.search(val)
            if m:
                size, unit = float(m.group(1)), m.group(2).upper()
                if unit == "T":
                    total += int(size * 1024)
                elif unit == "G" or unit == "":
                    total += int(size)
                elif unit == "M":
                    total += max(1, int(size // 1024))
        return total

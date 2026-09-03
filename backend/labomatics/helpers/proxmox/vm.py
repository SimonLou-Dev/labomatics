"""Client Proxmox pour gérer les VMs QEMU."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable

from labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxNotFoundError,
    ProxmoxServerError,
    urls,
)


class ProxmoxVMClient:
    """Client Proxmox pour gérer les VMs QEMU et conteneurs."""

    def __init__(
        self,
        proxmox_client: ProxmoxClientPool,
        wait_for_task_fn: Callable[[str, str], None] | None = None,
    ) -> None:
        """Initialise le client VM.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
            wait_for_task_fn: Fonction partagée pour attendre les tâches (optionnelle, pour fallback local).
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client
        self._wait_for_task_fn = wait_for_task_fn

    async def get_next_vmid(self) -> int:
        """Obtient le prochain VMID disponible du cluster.

        Returns:
            Prochain VMID disponible.

        Raises:
            RuntimeError: Problème API.
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(f"{urls.BASE}/cluster/nextid", cache=False)
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to get next VMID: {e}") from e

        data = resp.get("data")
        if not data:
            raise RuntimeError("No VMID returned from nextid endpoint")
        return int(data)

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

    async def find_node_by_name(self, vm_name: str) -> str | None:
        """Trouve le nœud hébergeant une VM par son nom.

        Args:
            vm_name: Nom de la VM.

        Returns:
            Nom du nœud ou None si VM non trouvée.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.CLUSTER_RESOURCES, params={"type": "vm"}, cache=False
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch cluster resources: {e}") from e

        resources = resp.get("data", [])
        for r in resources:
            if r.get("name") == vm_name:
                node = r.get("node")
                return str(node) if node is not None else None
        return None

    async def find_vmid_by_name(self, vm_name: str) -> int | None:
        """Trouve l'ID d'une VM par son nom.

        Args:
            vm_name: Nom de la VM.

        Returns:
            VMID ou None si VM non trouvée.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.CLUSTER_RESOURCES, params={"type": "vm"}, cache=False
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to fetch cluster resources: {e}") from e

        resources = resp.get("data", [])
        for r in resources:
            if r.get("name") == vm_name:
                return int(r.get("vmid", -1))
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

    async def clone(
        self,
        vm_name: str,
        vm_storage: str,
        source_id: int,
        dest_node: str | None = None,
        vmid: int | None = None,
        pool: str | None = None,
        full_clone: bool = True,
    ) -> tuple[str, int]:
        """Clone une VM à partir d'une template.

        Args:
            vm_name: Nom de la VM clonée.
            vm_storage: Storage device de destination (ex: "local").
            source_id: VMID de la template source.
            dest_node: Nœud de destination (auto-sélectionné si absent).
            vmid: ID de la VM (auto-assigné par Proxmox si absent).
            pool: Pool de destination.
            full_clone: Clonage complet (True) ou lié (False).

        Returns:
            Tuple (node, vmid) de la VM clonée.

        Raises:
            RuntimeError: Si la template n'est pas trouvée ou le clone échoue.
        """
        source_node = await self.find_node(source_id)
        if source_node is None:
            raise RuntimeError(f"Template VMID {source_id} not found on cluster")

        if dest_node is None:
            dest_node = await self.pick_node()

        # Obtenir le prochain VMID si pas fourni (évite les collisions)
        if vmid is None:
            vmid = await self.get_next_vmid()

        clone_args = {
            "name": vm_name,
            "full": 1 if full_clone else 0,
            "storage": vm_storage,
            "target": dest_node,
            "newid": vmid,
        }

        if pool is not None:
            clone_args["pool"] = pool

        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.post(
                    urls.qemu_clone(source_node, source_id), data=clone_args
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to clone VM {source_id}: {e}") from e

        # Extraire l'UPID et attendre
        # Proxmox retourne l'UPID comme string directement dans 'data'
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Clone response: {resp}")

        upid = resp.get("data")
        if isinstance(upid, dict):
            # Si c'est un dict, chercher l'UPID dedans
            upid = upid.get("id") or upid.get("upid")
        if not upid:
            raise RuntimeError(f"No UPID returned from clone request. Response: {resp}")

        logger.info(f"Extracted UPID: {upid} (type: {type(upid).__name__})")

        if self._wait_for_task_fn:
            await self._wait_for_task_fn(source_node, upid)
        else:
            raise RuntimeError("No wait_for_task function provided")

        # Résoudre le vmid réel (rechercher par nom sur dest_node)
        # Laisser le temps à Proxmox de mettre à jour l'index
        await asyncio.sleep(1)

        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.CLUSTER_RESOURCES, params={"type": "vm"}, cache=False
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to find cloned VM: {e}") from e

        resources = resp.get("data", [])
        for r in resources:
            if r.get("node") == dest_node and r.get("name") == vm_name:
                return dest_node, int(r.get("vmid"))

        raise RuntimeError(f"Cloned VM {vm_name} not found on {dest_node}")

    async def config(self, node: str, vmid: int, **args) -> None:
        """Configure une VM (cloud-init, hardware, etc.).

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.
            **args: Arguments de config (ex: cores=2, memory=512, ipconfig0=...).

        Raises:
            RuntimeError: Si la configuration échoue.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(urls.qemu_config(node, vmid), data=args)
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to configure VM {vmid} on {node}: {e}"
                ) from e

    async def start(self, node: str, vmid: int) -> None:
        """Démarre une VM.

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.

        Raises:
            RuntimeError: Si le démarrage échoue.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.post(urls.qemu_status_start(node, vmid))
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to start VM {vmid} on {node}: {e}") from e

        upid = resp.get("data")
        if upid and self._wait_for_task_fn:
            await self._wait_for_task_fn(node, upid)

    async def get_config(self, node: str, vmid: int) -> dict:
        """Récupère la configuration actuelle d'une VM.

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.

        Returns:
            Dict de configuration Proxmox.

        Raises:
            RuntimeError: Si la récupération échoue.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.qemu_config(node, vmid), cache=False)
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to get VM {vmid} config on {node}: {e}"
                ) from e

        return resp.get("data", {})

"""Client Proxmox pour gérer les pools."""

from labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxServerError,
    urls,
)


class ProxmoxPoolClient:
    """Client pour gérer les pools Proxmox."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client pools.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def exists(self, pool_name: str) -> bool:
        """Vérifie si un pool existe.

        Args:
            pool_name: Nom du pool.

        Returns:
            True si le pool existe, False sinon.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                # Utiliser GET /pools?poolid=... pour éviter la 500
                resp = await client.get(
                    urls.POOLS, params={"poolid": pool_name}, cache=True
                )
                pools = resp.get("data", [])
                return len(pools) > 0
            except Exception:
                # En cas d'erreur, supposer que le pool n'existe pas
                return False

    async def ensure_exists(self, pool_name: str, comment: str = "") -> None:
        """Crée le pool s'il n'existe pas.

        Args:
            pool_name: Nom du pool.
            comment: Commentaire descriptif du pool.
        """
        if not await self.exists(pool_name):
            await self.create(pool_name, comment)

    async def create(self, pool_name: str, comment: str = "") -> None:
        """Crée un pool Proxmox.

        Args:
            pool_name: Nom du pool.
            comment: Commentaire descriptif du pool.

        Raises:
            ProxmoxServerError: Si le pool existe déjà ou problème de création.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.post(
                    urls.POOLS,
                    data={"poolid": pool_name, "comment": comment},
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to create pool {pool_name}: {e}") from e

    async def delete(self, pool_name: str) -> None:
        """Supprime un pool Proxmox (doit être vide).

        Args:
            pool_name: Nom du pool.

        Raises:
            ProxmoxServerError: Si le pool n'est pas vide ou problème de suppression.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.delete(urls.pool_path(pool_name))
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to delete pool {pool_name}: {e}") from e

    async def add_vm(self, pool_name: str, vmid: int) -> None:
        """Ajoute une VM ou conteneur à un pool.

        Args:
            pool_name: Nom du pool.
            vmid: ID de la VM/LXC.

        Raises:
            ProxmoxServerError: Si le pool n'existe pas ou problème d'ajout.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(
                    urls.pool_path(pool_name),
                    data={"vms": str(vmid)},
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to add VM {vmid} to pool {pool_name}: {e}"
                ) from e

    async def get_vms(self, pool_name: str) -> list[dict]:
        """Retourne les VMs QEMU d'un pool.

        Args:
            pool_name: Nom du pool.

        Returns:
            Liste des VMs dans le pool.

        Raises:
            ProxmoxServerError: Si le pool n'existe pas ou problème de lecture.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.pool_path(pool_name), cache=True)
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch VMs from pool {pool_name}: {e}"
                ) from e

        pool_data = resp.get("data", {})
        members = pool_data.get("members", [])
        return [m for m in members if m.get("type") == "qemu"]

    async def get_lxcs(self, pool_name: str) -> list[dict]:
        """Retourne les conteneurs LXC d'un pool.

        Args:
            pool_name: Nom du pool.

        Returns:
            Liste des LXCs dans le pool.

        Raises:
            ProxmoxServerError: Si le pool n'existe pas ou problème de lecture.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.pool_path(pool_name), cache=True)
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to fetch LXCs from pool {pool_name}: {e}"
                ) from e

        pool_data = resp.get("data", {})
        members = pool_data.get("members", [])
        return [m for m in members if m.get("type") == "lxc"]

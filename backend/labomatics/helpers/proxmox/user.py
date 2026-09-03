"""Client Proxmox pour gérer les utilisateurs."""

from labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxServerError,
    urls,
)


class ProxmoxUserClient:
    """Client pour gérer les utilisateurs Proxmox."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client utilisateurs.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def exists(self, userid: str) -> bool:
        """Vérifie si un utilisateur existe en listant tous les users.

        Args:
            userid: ID utilisateur au format user@realm.

        Returns:
            True si l'utilisateur existe, False sinon.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(urls.ACCESS_USERS, cache=False)
                users = resp.get("data", [])
                return any(u.get("userid") == userid for u in users)
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to check user existence: {e}") from e

    async def create(
        self,
        userid: str,
        comment: str = "",
    ) -> None:
        """Crée un nouvel utilisateur Proxmox.

        Args:
            userid: ID utilisateur au format user@realm (ex: "labomatics@pve").
            comment: Commentaire optionnel (défaut: "Créé par labomatics").

        Raises:
            ProxmoxServerError: Si l'utilisateur existe déjà ou problème de création.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.post(
                    urls.ACCESS_USERS,
                    data={
                        "userid": userid,
                        "comment": comment or "Créé par labomatics",
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to create user {userid}: {e}"
                ) from e

    async def delete(self, userid: str) -> None:
        """Supprime un utilisateur Proxmox.

        Args:
            userid: ID utilisateur au format user@realm.

        Raises:
            ProxmoxServerError: Si l'utilisateur n'existe pas ou problème de suppression.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.delete(urls.access_user(userid))
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to delete user {userid}: {e}") from e

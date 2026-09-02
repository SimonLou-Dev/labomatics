"""Client Proxmox pour gérer les tokens API."""

from backend.labomatics.helpers.proxmox.api import (
    ProxmoxClientPool,
    ProxmoxNotFoundError,
    ProxmoxServerError,
    urls,
)


class ProxmoxTokenClient:
    """Client pour gérer les tokens API Proxmox."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client tokens.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def exists(self, userid: str, token_name: str = "labomatics") -> bool:  # noqa: S107
        """Vérifie si un token API existe.

        Args:
            userid: ID utilisateur au format user@realm.
            token_name: Nom du token (défaut: "labomatics").

        Returns:
            True si le token existe, False sinon.

        Raises:
            ProxmoxServerError: Problème API.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.get(urls.access_user_token(userid, token_name), cache=True)
                return True
            except ProxmoxNotFoundError:
                return False
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to check token existence for {userid}: {e}"
                ) from e

    async def create_student(
        self,
        userid: str,
        token_name: str = "labomatics",  # noqa: S107
    ) -> tuple[str, str]:
        """Crée un token API sans séparation de privilèges.

        Args:
            userid: ID utilisateur au format user@realm.
            token_name: Nom du token (défaut: "labomatics").

        Returns:
            (full_token_id, secret) — ex: ("jdupont@pve!labomatics", "xxxxxxxx-...")

        Raises:
            ProxmoxServerError: Si le token existe déjà ou problème de création.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.post(
                    urls.access_user_token(userid, token_name),
                    data={
                        "privsep": 0,
                        "comment": "labomatics",
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to create token {token_name} for {userid}: {e}"
                ) from e

        data = resp.get("data", {})
        return data["full-tokenid"], data["value"]

    async def delete_student(
        self,
        userid: str,
        token_name: str = "labomatics",  # noqa: S107
    ) -> None:
        """Supprime le token API d'un utilisateur.

        Args:
            userid: ID utilisateur au format user@realm.
            token_name: Nom du token (défaut: "labomatics").

        Raises:
            ProxmoxServerError: Si le token n'existe pas ou problème de suppression.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.delete(urls.access_user_token(userid, token_name))
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to delete token {token_name} for {userid}: {e}"
                ) from e

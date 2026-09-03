"""Client async Proxmox avec httpx."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import httpx
from cachetools import TTLCache

from .errors import (
    ProxmoxAPIError,
    ProxmoxAuthError,
    ProxmoxConflictError,
    ProxmoxConnectionError,
    ProxmoxNotFoundError,
    ProxmoxServerError,
    ProxmoxTimeoutError,
    ProxmoxValidationError,
)

T = TypeVar("T")


class AsyncProxmoxClient:
    """Client async Proxmox avec httpx, auth, caching, et gestion d'erreur complète."""

    def __init__(
        self,
        url: str,
        token_id: str,
        token_secret: str,
        timeout: float = 30.0,
        cache_ttl: int = 300,
        max_connections: int = 50,
        max_keepalive: int = 20,
    ) -> None:
        """Initialise le client Proxmox.

        Args:
            url: URL du serveur Proxmox (ex: "https://proxmox.example.com:8006").
            token_id: ID du token API.
            token_secret: Secret du token API.
            timeout: Timeout des requêtes en secondes.
            cache_ttl: TTL du cache en secondes.
            max_connections: Nombre max de connexions HTTP.
            max_keepalive: Nombre max de connexions keepalive.

        Raises:
            ValueError: Si les paramètres sont invalides.
            ProxmoxConnectionError: Problème de connexion.
        """
        if not url or not token_id or not token_secret:
            raise ValueError("url, token_id, et token_secret sont obligatoires")

        self._base_url = url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)
        self._cache: TTLCache = TTLCache(maxsize=5000, ttl=cache_ttl)

        # Headers d'authentification (format: PVEAPIToken=USER@REALM!TOKENID=UUID)
        auth_header = f"PVEAPIToken={token_id}={token_secret}"

        # Client httpx avec connexion pooling
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=self._timeout,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            ),
            verify=False,  # noqa: S501
        )

    async def get(
        self, path: str, params: dict[str, Any] | None = None, cache: bool = True
    ) -> dict:
        """Effectue une requête GET.

        Args:
            path: Chemin API (ex: "/api2/json/nodes").
            params: Paramètres de requête optionnels.
            cache: Utiliser le cache (défaut: True).

        Returns:
            Réponse JSON parsée.

        Raises:
            ProxmoxAuthError: Authentification échouée (401, 403).
            ProxmoxNotFoundError: Ressource non trouvée (404).
            ProxmoxServerError: Erreur serveur (5xx).
            ProxmoxConnectionError: Problème de connexion.
        """
        cache_key = (path, tuple(sorted((params or {}).items())))

        if cache and cache_key in self._cache:
            return self._cache[cache_key]

        try:
            resp = await self._client.get(path, params=params)
            data = self._handle_response(resp)

            if cache:
                self._cache[cache_key] = data

            return data
        except httpx.TimeoutException as e:
            raise ProxmoxTimeoutError(
                f"GET {path} timeout après {self._timeout.timeout}s"
            ) from e
        except httpx.NetworkError as e:
            raise ProxmoxConnectionError(f"Erreur réseau GET {path}: {e}") from e
        except ProxmoxAPIError:
            raise
        except Exception as e:
            raise ProxmoxConnectionError(f"Erreur GET {path}: {e}") from e

    async def post(self, path: str, data: dict[str, Any] | None = None) -> dict:
        """Effectue une requête POST.

        Args:
            path: Chemin API.
            data: Données POST.

        Returns:
            Réponse JSON parsée.

        Raises:
            ProxmoxAuthError: Authentification échouée.
            ProxmoxValidationError: Données invalides (400).
            ProxmoxConflictError: Ressource en conflit (409).
            ProxmoxServerError: Erreur serveur.
            ProxmoxConnectionError: Problème de connexion.
        """
        try:
            resp = await self._client.post(path, data=data or {})
            return self._handle_response(resp)
        except httpx.TimeoutException as e:
            raise ProxmoxTimeoutError(
                f"POST {path} timeout après {self._timeout.timeout}s"
            ) from e
        except httpx.NetworkError as e:
            raise ProxmoxConnectionError(f"Erreur réseau POST {path}: {e}") from e
        except ProxmoxAPIError:
            raise
        except Exception as e:
            raise ProxmoxConnectionError(f"Erreur POST {path}: {e}") from e

    async def put(self, path: str, data: dict[str, Any] | None = None) -> dict:
        """Effectue une requête PUT.

        Args:
            path: Chemin API.
            data: Données PUT.

        Returns:
            Réponse JSON parsée.

        Raises:
            ProxmoxAuthError: Authentification échouée.
            ProxmoxValidationError: Données invalides.
            ProxmoxServerError: Erreur serveur.
            ProxmoxConnectionError: Problème de connexion.
        """
        try:
            resp = await self._client.put(path, data=data or {})
            return self._handle_response(resp)
        except httpx.TimeoutException as e:
            raise ProxmoxTimeoutError(
                f"PUT {path} timeout après {self._timeout.timeout}s"
            ) from e
        except httpx.NetworkError as e:
            raise ProxmoxConnectionError(f"Erreur réseau PUT {path}: {e}") from e
        except ProxmoxAPIError:
            raise
        except Exception as e:
            raise ProxmoxConnectionError(f"Erreur PUT {path}: {e}") from e

    async def delete(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Effectue une requête DELETE.

        Args:
            path: Chemin API.
            params: Paramètres de requête optionnels.

        Returns:
            Réponse JSON parsée.

        Raises:
            ProxmoxAuthError: Authentification échouée.
            ProxmoxNotFoundError: Ressource non trouvée.
            ProxmoxServerError: Erreur serveur.
            ProxmoxConnectionError: Problème de connexion.
        """
        try:
            resp = await self._client.delete(path, params=params)
            return self._handle_response(resp)
        except httpx.TimeoutException as e:
            raise ProxmoxTimeoutError(
                f"DELETE {path} timeout après {self._timeout.timeout}s"
            ) from e
        except httpx.NetworkError as e:
            raise ProxmoxConnectionError(f"Erreur réseau DELETE {path}: {e}") from e
        except ProxmoxAPIError:
            raise
        except Exception as e:
            raise ProxmoxConnectionError(f"Erreur DELETE {path}: {e}") from e

    def _handle_response(self, resp: httpx.Response) -> dict:
        """Traite une réponse HTTP.

        Args:
            resp: Réponse httpx.

        Returns:
            Réponse JSON parsée.

        Raises:
            ProxmoxAuthError: 401, 403.
            ProxmoxNotFoundError: 404.
            ProxmoxValidationError: 400.
            ProxmoxConflictError: 409.
            ProxmoxServerError: 5xx.
            ProxmoxAPIError: Autres erreurs.
        """
        try:
            data = resp.json() if resp.content else {}
        except Exception:
            data = {"error": resp.text}

        status = resp.status_code
        error_msg = data.get("errors", data.get("error", "Unknown error"))

        # 2xx: succès
        if 200 <= status < 300:
            return data

        # 401, 403: authentification
        if status in (401, 403):
            raise ProxmoxAuthError(
                f"Authentification échouée ({status}): {error_msg}",
                status_code=status,
                response=data,
            )

        # 404: non trouvé
        if status == 404:
            raise ProxmoxNotFoundError(
                f"Ressource non trouvée (404): {error_msg}",
                status_code=status,
                response=data,
            )

        # 400: validation
        if status == 400:
            raise ProxmoxValidationError(
                f"Erreur de validation (400): {error_msg}",
                status_code=status,
                response=data,
            )

        # 409: conflit
        if status == 409:
            raise ProxmoxConflictError(
                f"Conflit (409): {error_msg}",
                status_code=status,
                response=data,
            )

        # 5xx: erreur serveur
        if 500 <= status < 600:
            raise ProxmoxServerError(
                f"Erreur serveur ({status}): {error_msg}",
                status_code=status,
                response=data,
            )

        # Autres
        raise ProxmoxAPIError(
            f"Erreur API ({status}): {error_msg}",
            status_code=status,
            response=data,
        )

    async def close(self) -> None:
        """Ferme la connexion."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncProxmoxClient":
        """Context manager async."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Ferme à la sortie du context manager."""
        await self.close()


class ProxmoxClientPool:
    """Gère un pool de connexions Proxmox réutilisable pour un cluster."""

    def __init__(
        self,
        url: str,
        user: str,
        token_id: str,
        token_secret: str,
        decrypt_fn: Callable[[bytes], str] | None = None,
        timeout: float = 30.0,
        cache_ttl: int = 300,
        max_connections: int = 50,
        max_keepalive: int = 20,
    ) -> None:
        """Initialise le pool de connexions Proxmox.

        Args:
            url: URL du serveur Proxmox.
            user: Utilisateur propriétaire du token.
            token_id: Identifiant du token.
            token_secret: Secret du token (ou bytes chiffré si decrypt_fn fournie).
            decrypt_fn: Fonction optionnelle pour déchiffrer token_secret si bytes.
            timeout: Timeout des requêtes en secondes.
            cache_ttl: TTL du cache en secondes.
            max_connections: Nombre max de connexions HTTP.
            max_keepalive: Nombre max de connexions keepalive.

        Raises:
            ValueError: Si les paramètres sont invalides.
            ProxmoxConnectionError: Problème de connexion.
        """
        if decrypt_fn and isinstance(token_secret, bytes):
            secret = decrypt_fn(token_secret)
        else:
            secret = str(token_secret)

        pve_token_id = f"{user}!{token_id}"

        self._client: AsyncProxmoxClient = AsyncProxmoxClient(
            url=url,
            token_id=pve_token_id,
            token_secret=secret,
            timeout=timeout,
            cache_ttl=cache_ttl,
            max_connections=max_connections,
            max_keepalive=max_keepalive,
        )

    @asynccontextmanager
    async def get_context_manager(self) -> AsyncGenerator[AsyncProxmoxClient, None]:
        """Emprunte le client sans le fermer.

        Yields:
            AsyncProxmoxClient initialisé et prêt à l'usage.

        Example:
            async with pool.get_context_manager() as client:
                await client.get("/api2/json/nodes")
        """
        yield self._client

    async def close(self) -> None:
        """Ferme la connexion du pool."""
        await self._client.close()

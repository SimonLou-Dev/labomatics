"""Service d'authentification / autorisation (Keycloak OIDC).

Toute la logique de vérification est ici ; les dépendances FastAPI ne font que câbler.
"""

from __future__ import annotations

import logging
import time

import jwt
import requests
from fastapi import HTTPException, status

from labomatics.api.dto.auth import AuthUser
from labomatics.core.config.settings import settings

logger = logging.getLogger(__name__)

_JWKS_TTL_SECONDS = 300


class AuthService:
    """Service d'authentification et d'autorisation."""

    _jwks_cache: dict | None = None
    _jwks_fetched_at: float = 0.0

    @staticmethod
    def _fetch_public_keys() -> dict:
        """Récupère les clés publiques Keycloak (JWKS) depuis Keycloak."""
        certs_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/certs"
        )
        resp = requests.get(certs_url, verify=settings.tls_verify, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def _get_public_keys(cls, *, force_refresh: bool = False) -> dict:
        """Clés publiques Keycloak, mises en cache avec une durée de vie limitée.

        Contrairement à un cache à vie, la JWKS est rafraîchie après
        `_JWKS_TTL_SECONDS` ou immédiatement si un `kid` inconnu est rencontré
        (rotation de clé côté Keycloak).
        """
        now = time.monotonic()
        if (
            force_refresh
            or cls._jwks_cache is None
            or now - cls._jwks_fetched_at > _JWKS_TTL_SECONDS
        ):
            cls._jwks_cache = cls._fetch_public_keys()
            cls._jwks_fetched_at = now
        return cls._jwks_cache

    @staticmethod
    def _claims_to_user(claims: dict) -> AuthUser:
        """Convertit les claims JWT en AuthUser."""
        roles = claims.get("realm_access", {}).get("roles", [])
        if isinstance(roles, str):
            roles = [roles]
        return AuthUser(
            subject=claims.get("sub", ""),
            username=claims.get("preferred_username", ""),
            email=claims.get("email", ""),
            roles=roles,
        )

    @staticmethod
    def authenticate(token: str | None) -> AuthUser:
        """Vérifie le token et retourne l'utilisateur. Lève 401 si invalide."""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token manquant"
            )
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            jwk = AuthService._find_jwk(kid)
            if jwk is None:
                # kid inconnu : la JWKS a peut-être tourné, on force un rechargement
                jwk = AuthService._find_jwk(kid, force_refresh=True)
            if jwk is None:
                raise jwt.InvalidTokenError(f"Kid inconnu: {kid}")

            signing_key = jwt.PyJWK.from_dict(jwk).key
            issuer = (
                f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
            )
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=settings.keycloak_client_id,
                issuer=issuer,
            )
            azp = claims.get("azp")
            if azp != settings.keycloak_client_id:
                raise jwt.InvalidTokenError(f"azp inattendu: {azp}")
        except jwt.PyJWTError as exc:
            logger.error("JWT decode error: %s", str(exc), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token invalide: {exc!s}",
            ) from exc
        return AuthService._claims_to_user(claims)

    @staticmethod
    def _find_jwk(kid: str | None, *, force_refresh: bool = False) -> dict | None:
        """Cherche la clé JWK correspondant au `kid` du token."""
        public_keys = AuthService._get_public_keys(force_refresh=force_refresh)
        return next(
            (k for k in public_keys.get("keys", []) if k.get("kid") == kid), None
        )

    @staticmethod
    def ensure_role(user: AuthUser, required_role: str) -> AuthUser:
        """Lève 403 si l'utilisateur n'a pas le rôle requis."""
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle '{required_role}' requis",
            )
        return user

    @staticmethod
    def exchange_code_for_token(code: str, code_verifier: str | None = None) -> dict:
        """Échange le code OAuth2 (+ PKCE code_verifier) contre un access/refresh token."""
        token_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/token"
        )
        app_base = (settings.url_prefix or "").strip("/")
        parts = [p for p in [app_base, "v1", "auth", "callback"] if p]
        redirect_uri_path = "/" + "/".join(parts)
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "code": code,
            "redirect_uri": f"{settings.app_url.rstrip('/')}{redirect_uri_path}",
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        resp = requests.post(
            token_url, data=data, verify=settings.tls_verify, timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Rafraîchit l'access token avec le refresh token."""
        token_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/token"
        )
        data = {
            "grant_type": "refresh_token",
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "refresh_token": refresh_token,
        }
        resp = requests.post(
            token_url, data=data, verify=settings.tls_verify, timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def revoke_refresh_token(refresh_token: str) -> None:
        """Révoque le refresh token côté Keycloak (appelé au logout)."""
        logout_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/logout"
        )
        data = {
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "refresh_token": refresh_token,
        }
        resp = requests.post(
            logout_url, data=data, verify=settings.tls_verify, timeout=10
        )
        resp.raise_for_status()

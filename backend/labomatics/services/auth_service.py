"""Service d'authentification / autorisation (Keycloak OIDC).

Toute la logique de vérification est ici ; les dépendances FastAPI ne font que câbler.
"""

from __future__ import annotations

from functools import lru_cache

import requests
from fastapi import HTTPException, status
from jose import JWTError, jwt

from labomatics.api.dto.auth import AuthUser
from labomatics.core.config.settings import settings


class AuthService:
    """Service d'authentification et d'autorisation."""

    @staticmethod
    @lru_cache
    def _get_public_keys() -> dict:
        """Récupère les clés publiques Keycloak en cache."""
        certs_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/certs"
        )
        resp = requests.get(certs_url, verify=False, timeout=10)  # noqa: S501
        resp.raise_for_status()
        return resp.json()

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
            public_keys = AuthService._get_public_keys()
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = None
            for key in public_keys.get("keys", []):
                if key.get("kid") == unverified_header.get("kid"):
                    rsa_key = key
                    break
            if not rsa_key:
                raise JWTError(f"Kid not found: {unverified_header.get('kid')}")

            claims = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=settings.keycloak_client_id,
                options={"verify_aud": False},
            )
        except JWTError as exc:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("JWT decode error: %s", str(exc), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token invalide: {exc!s}",
            ) from exc
        return AuthService._claims_to_user(claims)

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
    def exchange_code_for_token(code: str) -> dict:
        """Échange le code OAuth2 contre un access token + refresh token."""
        token_url = (
            f"{settings.keycloak_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/token"
        )
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "code": code,
            "redirect_uri": f"{settings.app_url.rstrip('/')}/api/v1/auth/callback",
        }
        resp = requests.post(token_url, data=data, verify=False, timeout=10)  # noqa: S501
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
        resp = requests.post(token_url, data=data, verify=False, timeout=10)  # noqa: S501
        resp.raise_for_status()
        return resp.json()

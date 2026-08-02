"""Routes d'authentification OAuth2/OIDC."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from labomatics.api.deps.auth import CurrentUser
from labomatics.api.dto.auth import MeDTO
from labomatics.core.config.settings import settings
from labomatics.core.connectors.redis import get_redis_async
from labomatics.services.auth_service import AuthService

redis_connector = get_redis_async().write

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(redirect: str = Query(default="/")):
    """Redirige vers Keycloak pour l'authentification (OAuth2 code flow).

    Args:
        redirect: URL de retour après login
    """
    state = secrets.token_urlsafe(32)
    # Stocke le state -> redirect_url mapping en Redis (expire après 10 min)
    await redis_connector.set(f"oauth2:state:{state}", redirect, ex=600)

    keycloak_auth_url = (
        f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/auth"
        f"?client_id={settings.keycloak_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.app_url.rstrip('/')}/api/v1/auth/callback"
        f"&scope=openid%20profile%20email"
        f"&state={state}"
    )
    return RedirectResponse(url=keycloak_auth_url)


@router.get("/callback")
async def callback(code: str = Query(...), state: str = Query(...)):
    """Callback OAuth2 — échange le code contre tokens et les stocke en cookies HTTPOnly."""
    redirect_url = await redis_connector.get(f"oauth2:state:{state}")
    if not redirect_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State invalide ou expiré",
        )
    # Supprimer le state après l'avoir utilisé
    await redis_connector.delete(f"oauth2:state:{state}")

    try:
        # Échange le code contre les tokens
        token_data = AuthService.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'obtenir l'access token",
            )

        # Redirige avec les cookies HTTPOnly
        response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        is_secure = settings.environment != "development"
        response.set_cookie(
            "access_token",
            access_token,
            max_age=expires_in,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            path="/",
        )
        if refresh_token:
            response.set_cookie(
                "refresh_token",
                refresh_token,
                max_age=30 * 24 * 3600,  # 30 jours
                httponly=True,
                secure=is_secure,
                samesite="lax",
                path="/",
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de l'échange du code: {e!s}",
        ) from e


@router.get("/logout")
async def logout() -> dict:
    """Logout (Keycloak-side)."""
    # Le vrai logout se fait côté Keycloak ; cette route est informelle
    logout_url = (
        f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/logout"
        f"?redirect_uri={settings.app_url}"
    )
    return {
        "logout_url": logout_url,
        "message": "Redirect to this URL to log out from Keycloak",
    }


@router.get("/me")
async def get_me(user: CurrentUser) -> MeDTO:
    """Retourne l'utilisateur courant + rôles (pour frontend et route guards)."""
    return MeDTO(subject=user.subject, username=user.username, roles=user.roles)

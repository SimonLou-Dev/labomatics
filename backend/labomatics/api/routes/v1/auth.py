"""Routes d'authentification OAuth2/OIDC."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from labomatics.api.deps.auth import CurrentUser
from labomatics.api.dto.auth import MeDTO
from labomatics.core.config.settings import settings
from labomatics.core.connectors.redis import get_redis_async
from labomatics.services.auth_service import AuthService

logger = logging.getLogger(__name__)

redis_connector = get_redis_async().write

router = APIRouter(prefix="/auth", tags=["auth"])


def _safe_redirect(redirect: str) -> str:
    """Neutralise un `redirect` qui pointerait vers un autre domaine (open redirect).

    Un chemin relatif est toujours accepté. Une URL absolue n'est acceptée que si
    elle partage l'origine du frontend configuré (`settings.front_url`) — le
    frontend (SPA en hash-routing) envoie volontairement une URL absolue vers
    lui-même, ce n'est donc pas réductible à un simple chemin relatif.
    """
    try:
        parsed = urlparse(redirect)
    except ValueError:
        return "/"
    if not parsed.netloc:
        return redirect
    allowed = urlparse(settings.front_url)
    if parsed.scheme in ("http", "https") and parsed.netloc == allowed.netloc:
        return redirect
    return "/"


def _generate_pkce_pair() -> tuple[str, str]:
    """Génère un couple (code_verifier, code_challenge) PKCE S256."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


@router.get("/login")
async def login(redirect: str = Query(default="/")):
    """Redirige vers Keycloak pour l'authentification (OAuth2 Authorization Code + PKCE).

    Args:
        redirect: URL de retour après login
    """
    redirect = _safe_redirect(redirect)
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce_pair()

    # Stocke le state -> redirect_url et le code_verifier PKCE en Redis (expire après 10 min)
    await redis_connector.set(f"oauth2:state:{state}", redirect, ex=600)
    await redis_connector.set(f"oauth2:verifier:{state}", code_verifier, ex=600)

    app_base = (settings.url_prefix or "").strip("/")
    parts = [p for p in [app_base, "v1", "auth", "callback"] if p]
    redirect_uri_path = "/" + "/".join(parts)
    keycloak_auth_url = (
        f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/auth"
        f"?client_id={settings.keycloak_client_id}"
        f"&response_type=code"
        f"&redirect_uri={settings.app_url.rstrip('/')}{redirect_uri_path}"
        f"&scope=openid%20profile%20email"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
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
    code_verifier = await redis_connector.get(f"oauth2:verifier:{state}")
    # Supprimer le state et le verifier après usage (anti-replay)
    await redis_connector.delete(f"oauth2:state:{state}")
    await redis_connector.delete(f"oauth2:verifier:{state}")

    try:
        # Échange le code (+ PKCE verifier) contre les tokens
        token_data = AuthService.exchange_code_for_token(code, code_verifier)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        refresh_expires_in = token_data.get("refresh_expires_in", 30 * 24 * 3600)

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
                max_age=refresh_expires_in,
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
async def logout(request: Request) -> RedirectResponse:
    """Révoque la session et redirige le navigateur vers la déconnexion Keycloak.

    Navigation directe (comme `/login`), pas un appel AJAX : la redirection
    vers Keycloak (puis retour sur le frontend) doit être suivie par le navigateur.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            AuthService.revoke_refresh_token(refresh_token)
        except Exception:
            logger.warning(
                "Impossible de révoquer le refresh token Keycloak au logout",
                exc_info=True,
            )

    logout_url = (
        f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/logout"
        f"?redirect_uri={settings.front_url}"
    )
    response = RedirectResponse(url=logout_url, status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


@router.get("/me")
async def get_me(user: CurrentUser) -> MeDTO:
    """Retourne l'utilisateur courant + rôles (pour frontend et route guards)."""
    return MeDTO(subject=user.subject, username=user.username, roles=user.roles)

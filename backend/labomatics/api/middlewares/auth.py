"""Middleware d'authentification global."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from labomatics.core.config.settings import settings
from labomatics.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware qui valide le JWT sur toutes les routes (sauf whitelist)."""

    # Routes publiques (sans auth requise)
    PUBLIC_PATHS = frozenset(
        {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
            "/v1/auth/login",
            "/v1/auth/callback",
            "/api/v1/ws/",  # WebSockets gèrent leur propre auth
            "/ws/",  # WebSockets gèrent leur propre auth
        }
    )

    async def dispatch(self, request: Request, call_next):
        """Valide le token JWT (depuis cookies) pour les routes protégées."""
        path = request.url.path

        # Ignorer les routes publiques
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        # Récupérer le token depuis les cookies
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        if not access_token:
            # Si pas d'access token mais qu'on a un refresh token, essayer de refresh
            if refresh_token:
                try:
                    logger.info("Access token missing, attempting refresh with refresh_token")
                    token_data = AuthService.refresh_access_token(refresh_token)
                    new_access_token = token_data.get("access_token")
                    new_refresh_token = token_data.get("refresh_token", refresh_token)
                    if new_access_token:
                        user = AuthService.authenticate(new_access_token)
                        request.state.user = user
                        request.state.new_access_token = new_access_token
                        request.state.new_refresh_token = new_refresh_token
                        logger.info("Token refreshed successfully from missing access_token")
                    else:
                        raise Exception("Pas d'access token dans la réponse refresh")
                except Exception as refresh_err:
                    logger.debug("Refresh failed when access token missing: %s", refresh_err)
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Session expirée. Veuillez vous reconnecter."},
                    )
            else:
                logger.warning("Access token missing and no refresh token for path: %s", path)
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token manquant"},
                )

        try:
            user = AuthService.authenticate(access_token)
            request.state.user = user
        except HTTPException as http_exc:
            logger.debug("Authentication failed with status %d: %s", http_exc.status_code, http_exc.detail)
            # Si le token est invalide et on a un refresh token, essayer le refresh
            if http_exc.status_code == 401 and refresh_token:
                try:
                    token_data = AuthService.refresh_access_token(refresh_token)
                    new_access_token = token_data.get("access_token")
                    new_refresh_token = token_data.get("refresh_token", refresh_token)
                    if new_access_token:
                        user = AuthService.authenticate(new_access_token)
                        request.state.user = user
                        # Les nouveaux tokens seront définis dans la réponse
                        request.state.new_access_token = new_access_token
                        request.state.new_refresh_token = new_refresh_token
                    else:
                        raise Exception("Pas d'access token dans la réponse refresh")
                except Exception as refresh_err:
                    logger.debug("Refresh token failed: %s", refresh_err)
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Session expirée. Veuillez vous reconnecter."
                        },
                    )
            else:
                return JSONResponse(
                    status_code=http_exc.status_code,
                    content={"detail": http_exc.detail},
                )
        except Exception as e:
            logger.error("Unexpected authentication error: %s", str(e), exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Erreur d'authentification"},
            )

        response = await call_next(request)

        # Si on a généré de nouveaux tokens, les mettre dans des cookies
        if hasattr(request.state, "new_access_token"):
            is_secure = settings.environment != "development"
            response.set_cookie(
                "access_token",
                request.state.new_access_token,
                max_age=3600,
                httponly=True,
                secure=is_secure,
                samesite="lax",
                path="/",
            )
            if hasattr(request.state, "new_refresh_token"):
                response.set_cookie(
                    "refresh_token",
                    request.state.new_refresh_token,
                    max_age=30 * 24 * 3600,  # 30 jours
                    httponly=True,
                    secure=is_secure,
                    samesite="lax",
                    path="/",
                )

        return response

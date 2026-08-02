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
        }
    )

    async def dispatch(self, request: Request, call_next):
        """Valide le token JWT (depuis cookies) pour les routes protégées."""
        path = request.url.path

        # Ignorer les routes publiques
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        # Debug: afficher les cookies reçus
        logger.info("Cookies reçus: %s", list(request.cookies.keys()))

        # Récupérer le token depuis les cookies
        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        if not access_token:
            logger.warning("Access token missing for path: %s", path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token manquant"},
            )

        try:
            logger.info(
                "Authenticating with access_token, first 20 chars: %s",
                access_token[:20],
            )
            user = AuthService.authenticate(access_token)
            request.state.user = user
            logger.info("Authentication successful for user: %s", user.username)
        except HTTPException as http_exc:
            logger.debug("Authentication failed with 401: %s", http_exc.detail)
            # Si le token est invalide et on a un refresh token, essayer le refresh
            if http_exc.status_code == 401 and refresh_token:
                try:
                    logger.info("Attempting token refresh...")
                    token_data = AuthService.refresh_access_token(refresh_token)
                    new_access_token = token_data.get("access_token")
                    if new_access_token:
                        user = AuthService.authenticate(new_access_token)
                        request.state.user = user
                        # Le nouveau token sera défini dans la réponse
                        request.state.new_access_token = new_access_token
                        logger.info("Token refreshed successfully")
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

        # Si on a généré un nouveau access token, le mettre dans un cookie
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

        return response

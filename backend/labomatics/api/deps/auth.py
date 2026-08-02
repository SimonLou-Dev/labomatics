"""Dépendances d'authentification (câblage mince vers auth_service)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPBearer

from labomatics.api.dto.auth import AuthUser
from labomatics.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False)


def current_user(request: Request) -> AuthUser:
    """Utilisateur courant (depuis request.state.user mis par le middleware)."""
    # Le middleware a déjà validé le token et mis l'utilisateur dans request.state.user
    if hasattr(request.state, "user"):
        return request.state.user

    # Fallback: essayer de récupérer depuis Authorization header (pour les tests/autres cas)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return AuthService.authenticate(token)

    # Sinon, lever 401
    return AuthService.authenticate(None)


def require_role(required_role: str):
    """Factory pour vérifier un rôle/permission spécifique."""

    def check_role(user: Annotated[AuthUser, Depends(current_user)]) -> AuthUser:
        return AuthService.ensure_role(user, required_role)

    return Annotated[AuthUser, Depends(check_role)]


CurrentUser = Annotated[AuthUser, Depends(current_user)]
RequireManageUser = require_role("manage_user")
RequireManageCluster = require_role("manage_cluster")

"""DTO d'authentification."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    """Utilisateur authentifié (issu du token Keycloak)."""

    subject: str
    username: str = ""
    email: str = ""
    roles: list[str] = Field(default_factory=list)


class MeDTO(BaseModel):
    """Utilisateur courant retourné par l'API."""

    subject: str
    username: str
    roles: list[str] = Field(default_factory=list)

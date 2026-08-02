"""DTO notification temps reel."""

from __future__ import annotations

from pydantic import BaseModel

from labomatics.constants import NotifType


class WsNotification(BaseModel):
    """Notification poussee a l'utilisateur (aligne sur le type front WsNotification)."""

    type: NotifType
    message: str
    entityId: int | None = None


class JobDTO(BaseModel):
    """Reference d'une tache asynchrone a suivre via `/ws/jobs/{jobId}`."""

    jobId: str


class RenderResponseDTO(BaseModel):
    """Reponse du rendu : indique si un rendu est necessaire et fournit jobId si oui."""

    needRender: bool
    jobId: str | None = None

"""Service de notifications temps reel via Redis pub/sub.

Deux canaux :
- notifications utilisateur : `notify:{user_id}` (toasts, retour generique) ;
- progression de tache : `job:{job_id}` (etapes ATLAS/OMEGA/render...).

Publication best-effort : une panne Redis ne casse jamais le flux de la requete.
"""

from __future__ import annotations

import json
import logging
from datetime import date

from labomatics.core.config.settings import settings

# from labomatics.core.context import current_user_id

logger = logging.getLogger(__name__)


class NotificationService:
    """Service de notifications temps reel via Redis pub/sub."""

    _PREFIX = f"{settings.redis_prefix}_{settings.environment}"
    _VISITORS_TTL = 60 * 60 * 48  # garde le compteur du jour 48h

    def __init__(self) -> None:
        """Constructeur."""
        pass

    @staticmethod
    def user_channel(user_id: str) -> str:
        prefix = f"{settings.redis_prefix}_{settings.environment}"
        return f"{prefix}:notify:{user_id}"

    @staticmethod
    def job_channel(job_id: str) -> str:
        prefix = f"{settings.redis_prefix}_{settings.environment}"
        return f"{prefix}:job:{job_id}"

    @staticmethod
    def _visitors_key() -> str:
        prefix = f"{settings.redis_prefix}_{settings.environment}"
        return f"{prefix}:visitors:{date.today().isoformat()}"

    async def _publish(self, channel: str, payload: str) -> None:
        """Publie sur Redis ; ne leve jamais (best-effort)."""
        try:
            pass
            # await get_redis_async().write.publish(channel, payload)
        except Exception as exc:  # connexion Redis indisponible, etc.
            logger.warning("Notification non publiee sur %s : %s", channel, exc)

    # async def notify(
    #     self,
    #     notif_type: NotifType,
    #     message: str,
    #     *,
    #     entity_id: int | None = None,
    #     user_id: str | None = None,
    # ) -> None:
    #     """Pousse une notification a l'utilisateur courant (X-USER-ID via ContextVar).

    #     `user_id` explicite prime ; sinon on lit le contexte de requete. No-op si aucun
    #     (appel hors requete ou client sans X-USER-ID) — la requete n'echoue jamais.
    #     """
    #     uid = user_id if user_id is not None else current_user_id()
    #     if not uid:
    #         return
    #     payload = WsNotification(type=notif_type, message=message, entityId=entity_id)
    #     await self._publish(self.user_channel(uid), payload.model_dump_json())

    # async def info(
    #     self, message: str, *, entity_id: int | None = None, user_id: str | None = None
    # ) -> None:
    #     await self.notify(NotifType.INFO, message, entity_id=entity_id, user_id=user_id)

    # async def success(
    #     self, message: str, *, entity_id: int | None = None, user_id: str | None = None
    # ) -> None:
    #     await self.notify(NotifType.SUCCESS, message, entity_id=entity_id, user_id=user_id)

    # async def warning(
    #     self, message: str, *, entity_id: int | None = None, user_id: str | None = None
    # ) -> None:
    #     await self.notify(NotifType.WARNING, message, entity_id=entity_id, user_id=user_id)

    # async def error(
    #     self, message: str, *, entity_id: int | None = None, user_id: str | None = None
    # ) -> None:
    #     await self.notify(NotifType.ERROR, message, entity_id=entity_id, user_id=user_id)

    async def publish_job_event(self, job_id: str, event: dict) -> None:
        """Publie un evenement de progression de tache (step_start/step_done/done/error...)."""
        await self._publish(self.job_channel(job_id), json.dumps(event))

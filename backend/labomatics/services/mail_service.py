"""Service d'envoi de mail (stub)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MailService:
    """Service d'envoi de mail."""

    async def send_mail(self, to: str, subject: str, body: str) -> None:
        """Envoie un mail (stub pour l'instant).

        TODO(#42): implémenter l'envoi SMTP réel une fois le provider choisi
        """
        logger.warning(
            "MailService.send_mail stub — mail non envoyé à %s: %s", to, subject
        )

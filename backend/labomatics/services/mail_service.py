"""Service d'envoi de mail via Brevo."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from brevo import AsyncBrevo
from brevo.core.api_error import ApiError
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

from labomatics.core.config.settings import settings
from labomatics.services.email_templates import EmailTemplateService, EmailType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MailService:
    """Service d'envoi de mail via Brevo."""

    def __init__(self) -> None:
        """Initialise le service de mail.

        Args:
            settings: Configuration de l'application
        """
        self.settings = settings
        self._client = AsyncBrevo(api_key=settings.brevo_api_key)
        self._template_service = EmailTemplateService()

    async def send_mail(
        self, to: str, subject: str, body: str, from_name: str | None = None
    ) -> None:
        """Envoie un mail via Brevo.

        Args:
            to: Adresse email destinataire
            subject: Sujet du mail
            body: Corps du mail (HTML)
            from_name: Nom de l'expéditeur (utilise BREVO_FROM_NAME par défaut)
        """
        if not self.settings.brevo_api_key:
            logger.warning(
                "MailService: BREVO_API_KEY non configurée, mail non envoyé à %s: %s",
                to,
                subject,
            )
            return

        try:
            return await self._client.transactional_emails.send_transac_email(
                subject=subject,
                html_content=body,
                sender=SendTransacEmailRequestSender(
                    name=from_name or self.settings.brevo_from_name,
                    email=self.settings.brevo_from_email,
                ),
                to=[
                    SendTransacEmailRequestToItem(
                        email=to,
                    )
                ],
            )

        except ApiError as e:
            logger.error("Erreur lors de l'envoi du mail à %s: %s", to, str(e))
            raise

    async def send_templated_mail(
        self,
        to: str,
        subject: str,
        email_type: EmailType,
        context: dict[str, Any],
        from_name: str | None = None,
    ) -> None:
        """Envoie un mail templé via Brevo.

        Args:
            to: Adresse email destinataire
            subject: Sujet du mail
            email_type: Type de template à utiliser
            context: Variables pour le rendu Jinja2
            from_name: Nom de l'expéditeur (utilise BREVO_FROM_NAME par défaut)
        """
        html_content = self._template_service.render(email_type, context)
        return await self.send_mail(to, subject, html_content, from_name)

"""Page « E-mail » : Brevo pour le backend, SMTP pour Keycloak."""

from __future__ import annotations

from labomatics_cli.installer.checks import CheckError, Checks
from labomatics_cli.installer.pages.base import Page, offload
from labomatics_cli.tui import (
    ConfirmField,
    PasswordField,
    Step,
    TextField,
    WizardContext,
)
from labomatics_cli.tui import validators as v


def mail_enabled(ctx: WizardContext) -> bool:
    """Indique si l'envoi d'e-mails est configuré.

    Args:
        ctx: Contexte de l'assistant.

    Returns:
        True si « Configurer l'envoi d'e-mails » est coché.
    """
    return bool(ctx.values.get("mail.enabled"))


class MailPage(Page):
    """Configuration Brevo et SMTP, testée à la soumission."""

    title = "E-mail"
    section = "mail"

    def __init__(self, checks: Checks | None = None) -> None:
        """Initialise la page.

        Args:
            checks: Contrôles réseau (SMTP, Brevo), remplaçables en test.
        """
        self.checks = checks or Checks()

    def build(self) -> Step:
        """Construit l'étape e-mail.

        Returns:
            L'étape, dont `on_submit` teste SMTP puis Brevo.
        """
        fields = [
            ConfirmField(
                "Envoi d'e-mails", key="mail.enabled", default=True, required=True
            ),
            PasswordField(
                "Clé API Brevo",
                key="mail.brevo_api_key",
                required=True,
                visible_if=mail_enabled,
                helper="Utilisée par le backend",
            ),
            TextField(
                "Adresse expéditrice",
                key="mail.from_email",
                required=True,
                visible_if=mail_enabled,
                validator=v.Email(),
            ),
            TextField(
                "Nom expéditeur",
                key="mail.from_name",
                default="Labomatics",
                required=True,
                visible_if=mail_enabled,
                validator=v.Length(1, 64),
            ),
            TextField(
                "Serveur SMTP",
                key="mail.smtp_host",
                required=True,
                visible_if=mail_enabled,
                helper="Utilisé par Keycloak (réinitialisation de mot de passe)",
                validator=v.Host(),
            ),
            TextField(
                "Port SMTP",
                key="mail.smtp_port",
                default=587,
                required=True,
                visible_if=mail_enabled,
                validator=v.Port(),
            ),
            TextField(
                "Utilisateur SMTP", key="mail.smtp_user", visible_if=mail_enabled
            ),
            PasswordField(
                "Mot de passe SMTP", key="mail.smtp_password", visible_if=mail_enabled
            ),
            ConfirmField(
                "STARTTLS",
                key="mail.smtp_starttls",
                default=True,
                visible_if=mail_enabled,
            ),
        ]
        return Step(
            self.title,
            fields,
            on_submit=self._submit,
            loading_text="Test SMTP et Brevo…",
        )

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Teste la connexion SMTP, puis la clé Brevo.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur, ou None (aussi quand l'envoi est désactivé).
        """
        values = ctx.values
        if not values.get("mail.enabled"):
            return None
        try:
            await offload(
                self.checks.smtp.check,
                values["mail.smtp_host"],
                int(values["mail.smtp_port"]),
                bool(values.get("mail.smtp_starttls", True)),
                values.get("mail.smtp_user", ""),
                values.get("mail.smtp_password", ""),
            )
            await offload(self.checks.brevo.check, values["mail.brevo_api_key"])
        except CheckError as exc:
            return str(exc)
        return None

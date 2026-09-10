"""Service de rendu de templates d'email."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class EmailType(StrEnum):
    """Types d'emails disponibles."""

    ENROLLMENT = "enrollment"
    LAB_PROVISIONED = "lab_provisioned"
    PASSWORD_RESET = "password_reset"  # noqa: S105
    ACCOUNT_CREATED = "account_created"


class EmailTemplateService:
    """Service de rendu de templates d'email avec Jinja2."""

    def __init__(self) -> None:
        """Initialise le service de templates."""
        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, email_type: EmailType, context: dict[str, Any]) -> str:
        """Rend une template d'email.

        Args:
            email_type: Type d'email (enum)
            context: Variables pour la template Jinja2

        Returns:
            HTML rendu du mail
        """
        template = self.env.get_template(f"{email_type.value}.html")
        return template.render(**context)

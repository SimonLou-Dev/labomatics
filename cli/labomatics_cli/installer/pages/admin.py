"""Page « Compte d'administration » : premier administrateur Keycloak."""

from __future__ import annotations

from typing import Optional

from labomatics_cli.installer.pages.base import Page
from labomatics_cli.installer.pages.fields import HintField
from labomatics_cli.models.install_config import AdminSection
from labomatics_cli.tui import Step, TextField, WizardContext
from labomatics_cli.tui import validators as v


def username_hint(ctx: WizardContext) -> Optional[str]:
    """Identifiant de connexion calculé à partir du prénom et du nom saisis.

    Args:
        ctx: Contexte de l'assistant.

    Returns:
        Le texte « Identifiant : prenom.nom », ou None tant que le nom est vide.
    """
    first = str(ctx.values.get("admin.first_name") or "")
    last = str(ctx.values.get("admin.last_name") or "")
    if not first.strip() or not last.strip():
        return None
    account = AdminSection(email="a@b.c", first_name=first, last_name=last)
    return f"Identifiant de connexion : {account.username}"


class AdminPage(Page):
    """E-mail, prénom et nom de l'administrateur."""

    title = "Compte d'administration"
    section = "admin"

    def build(self) -> Step:
        """Construit l'étape du compte d'administration.

        Returns:
            L'étape ; l'identifiant calculé s'affiche sous le nom.
        """
        fields = [
            TextField(
                "E-mail",
                key="admin.email",
                required=True,
                validator=v.Email(),
            ),
            TextField(
                "Prénom",
                key="admin.first_name",
                required=True,
                validator=v.Length(1, 64),
            ),
            HintField(
                "Nom",
                key="admin.last_name",
                required=True,
                hint=username_hint,
                validator=v.Length(1, 64),
            ),
        ]
        return Step(self.title, fields)

"""Pages « Authentification » et « Fédération LDAP externe »."""

from __future__ import annotations

from labomatics_cli.installer.checks import CheckError, Checks
from labomatics_cli.installer.pages.base import Page, offload
from labomatics_cli.models.install_config import DirectoryMode, InstallConfig
from labomatics_cli.tui import (
    ConfirmField,
    PasswordField,
    RadioField,
    Step,
    TextField,
    WizardContext,
)
from labomatics_cli.tui import validators as v

DIRECTORY_KEY = "auth.directory"


def is_directory(ctx: WizardContext, mode: DirectoryMode) -> bool:
    """Indique si l'annuaire choisi est le mode demandé.

    Args:
        ctx: Contexte de l'assistant.
        mode: Mode d'annuaire testé.

    Returns:
        True si le choix courant correspond.
    """
    return ctx.values.get(DIRECTORY_KEY) == mode.value


class AuthPage(Page):
    """Choix de l'annuaire (aucun, local, externe) et de RADIUS."""

    title = "Authentification"
    section = "auth"

    def build(self) -> Step:
        """Construit l'étape d'authentification.

        Returns:
            L'étape ; RADIUS n'est proposé qu'avec un LDAP local.
        """
        fields = [
            RadioField(
                "Annuaire",
                [
                    (DirectoryMode.none.value, "Aucun"),
                    (DirectoryMode.local.value, "LDAP local"),
                    (DirectoryMode.external.value, "LDAP externe"),
                ],
                key=DIRECTORY_KEY,
                default=DirectoryMode.local.value,
                required=True,
            ),
            ConfirmField(
                "Serveur RADIUS",
                key="auth.radius",
                default=False,
                helper="Installe FreeRADIUS adossé à l'annuaire local",
                visible_if=lambda c: is_directory(c, DirectoryMode.local),
            ),
        ]
        return Step(self.title, fields)


class LdapPage(Page):
    """Fédération vers un annuaire LDAP externe (visible si « LDAP externe »)."""

    title = "Fédération LDAP externe"
    section = "ldap"

    def __init__(self, checks: Checks | None = None) -> None:
        """Initialise la page.

        Args:
            checks: Contrôles réseau (bind LDAP), remplaçables en test.
        """
        self.checks = checks or Checks()

    def is_saved(self, config: InstallConfig) -> bool:
        """Indique si la page est validée, ou sans objet hors « LDAP externe ».

        Args:
            config: Configuration sauvegardée du cluster.

        Returns:
            True si la section existe ou si l'annuaire n'est pas externe.
        """
        external = (
            config.auth is not None and config.auth.directory == DirectoryMode.external
        )
        return config.ldap is not None or not external

    def build(self) -> Step:
        """Construit l'étape LDAP externe.

        Returns:
            L'étape, dont `on_submit` teste le bind et les branches users/groups.
        """
        fields = [
            TextField(
                "URL du serveur",
                key="ldap.url",
                required=True,
                helper="Ex. ldaps://ldap.exemple.fr:636",
                validator=v.LdapUrl(),
            ),
            ConfirmField(
                "StartTLS",
                key="ldap.starttls",
                default=False,
                visible_if=lambda c: not str(c.values.get("ldap.url", ""))
                .lower()
                .startswith("ldaps://"),
            ),
            TextField(
                "Base DN",
                key="ldap.base_dn",
                required=True,
                helper="Utilisateurs dans ou=users,<base>, groupes dans ou=groups,<base>",
                validator=v.LdapDn(),
            ),
            TextField(
                "DN de bind",
                key="ldap.bind_dn",
                required=True,
                helper="Compte autorisé à écrire et supprimer dans ces deux branches",
                validator=v.LdapDn(),
            ),
            PasswordField("Mot de passe bind", key="ldap.bind_password", required=True),
            TextField("Attribut UUID", key="ldap.uuid_attr", default="entryUUID"),
            ConfirmField(
                "Synchro périodique",
                key="ldap.periodic_sync",
                default=False,
                helper="Synchronise régulièrement les changements de l'annuaire",
            ),
        ]
        return Step(
            self.title,
            fields,
            on_submit=self._submit,
            loading_text="Connexion à l'annuaire…",
            visible_if=lambda c: is_directory(c, DirectoryMode.external),
        )

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Teste le bind puis la présence des branches `ou=users` et `ou=groups`.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur, ou None.
        """
        values = ctx.values
        try:
            await offload(
                self.checks.ldap.check,
                values["ldap.url"],
                bool(values.get("ldap.starttls", False)),
                values["ldap.bind_dn"],
                values["ldap.bind_password"],
                values["ldap.base_dn"],
            )
        except CheckError as exc:
            return str(exc)
        return None

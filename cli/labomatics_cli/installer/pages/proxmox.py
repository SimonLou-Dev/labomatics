"""Page « Proxmox » : connexion à l'API, contrôle des droits et découverte du cluster."""

from __future__ import annotations

from typing import Callable, Collection

from labomatics_cli.installer.pages.base import (
    DATA_API,
    DATA_BRIDGES,
    DATA_NODES,
    DATA_STORAGES,
    Page,
    offload,
)
from labomatics_cli.installer.pages.rules import FreeClusterName
from labomatics_cli.installer.proxmox_api import (
    ProxmoxApi,
    ProxmoxError,
    ProxmoxPermissionError,
)
from labomatics_cli.tui import PasswordField, Step, TextField, WizardContext
from labomatics_cli.tui import validators as v

ApiFactory = Callable[[str, str, str, str], ProxmoxApi]


class ProxmoxPage(Page):
    """Connexion à Proxmox ; remplit `ctx.data` pour les pages suivantes."""

    title = "Proxmox"
    section = "proxmox"

    def __init__(
        self,
        api_factory: ApiFactory = ProxmoxApi,
        taken_names: Callable[[], Collection[str]] = lambda: (),
    ) -> None:
        """Initialise la page.

        Args:
            api_factory: Construit le client (url, user, token_id, secret) ; remplaçable en test.
            taken_names: Noms de cluster déjà utilisés, refusés à la saisie.
        """
        self.api_factory = api_factory
        self.taken_names = taken_names

    def build(self) -> Step:
        """Construit l'étape Proxmox.

        Returns:
            L'étape, dont `on_submit` teste la connexion et les droits.
        """
        fields = [
            TextField(
                "Nom du cluster",
                key="proxmox.cluster_name",
                default="labomatics",
                required=True,
                helper="Minuscules, chiffres, tirets. Sert au client Keycloak proxmox-<nom>.",
                validator=v.AllOf(
                    v.Regex(
                        r"^[a-z][a-z0-9-]{1,30}$",
                        "2 à 31 caractères : minuscules, chiffres, tirets, première lettre",
                    ),
                    FreeClusterName(self.taken_names),
                ),
            ),
            TextField(
                "URL du cluster",
                key="proxmox.url",
                required=True,
                helper="Ex. https://pve1.lab:8006",
                validator=v.Url(("https",)),
            ),
            TextField(
                "Utilisateur",
                key="proxmox.user",
                default="root@pam",
                required=True,
                helper="Format utilisateur@realm",
                validator=v.Regex(
                    r"^[^@\s]+@[A-Za-z0-9_.-]+$", "Format attendu : utilisateur@realm"
                ),
            ),
            TextField(
                "Nom du token",
                key="proxmox.token_id",
                required=True,
                helper="Partie après le « ! » de l'identifiant du token",
                validator=v.Regex(
                    r"^[A-Za-z][A-Za-z0-9_.-]*$",
                    "Lettres, chiffres, « . », « _ » et « - »",
                ),
            ),
            PasswordField(
                "Secret du token",
                key="proxmox.token_secret",
                required=True,
                helper="Décocher « Privilege Separation » à la création du token",
                validator=v.Uuid(),
            ),
        ]
        return Step(
            self.title,
            fields,
            on_submit=self._submit,
            loading_text="Connexion à Proxmox…",
        )

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Teste la connexion, les droits, puis met le cluster en cache.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur, ou None si tout est valide.
        """
        values = ctx.values
        try:
            await offload(
                self.load,
                ctx,
                values["proxmox.url"],
                values["proxmox.user"],
                values["proxmox.token_id"],
                values["proxmox.token_secret"],
            )
        except ProxmoxError as exc:
            return str(exc)
        return None

    def load(
        self, ctx: WizardContext, url: str, user: str, token_id: str, secret: str
    ) -> None:
        """Se connecte, contrôle le cluster et remplit `ctx.data`.

        Args:
            ctx: Contexte de l'assistant.
            url: URL du cluster.
            user: Utilisateur du token.
            token_id: Nom du token.
            secret: Secret du token.

        Raises:
            ProxmoxError: Connexion impossible, nœud hors ligne ou droits insuffisants.
        """
        api = self.api_factory(url, user, token_id, secret)
        api.version()
        nodes = api.nodes()
        offline = [n.name for n in nodes if not n.online]
        if offline:
            raise ProxmoxError(f"Nœuds hors ligne : {', '.join(offline)}")
        missing = api.missing_privileges()
        if missing:
            raise ProxmoxPermissionError(
                f"Droits insuffisants sur / (manque : {', '.join(missing)})"
            )
        ctx.data.update(
            {
                DATA_API: api,
                DATA_NODES: nodes,
                DATA_BRIDGES: api.common_bridges(),
                DATA_STORAGES: api.shared_storages(),
            }
        )

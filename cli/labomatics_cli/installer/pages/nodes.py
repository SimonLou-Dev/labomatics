"""Page « Accès SSH aux nœuds » : un mot de passe par nœud, pour la propagation des CA."""

from __future__ import annotations

import asyncio
from typing import Sequence

from labomatics_cli.installer.checks import CheckError, Checks
from labomatics_cli.installer.pages.base import DATA_NODES, Page, offload
from labomatics_cli.models.install_config import InstallConfig
from labomatics_cli.tui import Field, PasswordField, Step, TextField, WizardContext
from labomatics_cli.tui import validators as v


class NodesPage(Page):
    """Utilisateur, mot de passe et adresse SSH de chaque nœud découvert."""

    title = "Accès SSH aux nœuds"
    section = "nodes"

    def __init__(self, checks: Checks | None = None) -> None:
        """Initialise la page.

        Args:
            checks: Contrôles réseau (SSH), remplaçables en test.
        """
        self.checks = checks or Checks()

    def is_saved(self, config: InstallConfig) -> bool:
        """Indique si au moins un nœud a ses accès sauvegardés.

        Args:
            config: Configuration sauvegardée du cluster.

        Returns:
            True si `config.nodes` n'est pas vide.
        """
        return bool(config.nodes)

    def build(self) -> Step:
        """Construit l'étape (champs générés à chaque entrée, d'après les nœuds en cache).

        Returns:
            L'étape dont `on_submit` teste la connexion SSH de chaque nœud.
        """
        return Step(
            self.title,
            self._fields,
            on_submit=self._submit,
            loading_text="Connexion SSH aux nœuds…",
        )

    @staticmethod
    def _fields(ctx: WizardContext) -> Sequence[Field]:
        """Fabrique les trois champs de chaque nœud de `ctx.data`.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Utilisateur, mot de passe et adresse pour chaque nœud.
        """
        fields: list[Field] = []
        for node in ctx.data.get(DATA_NODES, []):
            prefix = f"nodes.{node.name}"
            fields += [
                TextField(
                    f"{node.name} : utilisateur",
                    key=f"{prefix}.user",
                    default="root",
                    required=True,
                ),
                PasswordField(
                    f"{node.name} : mot de passe",
                    key=f"{prefix}.password",
                    required=True,
                ),
                TextField(
                    f"{node.name} : adresse",
                    key=f"{prefix}.host",
                    default=node.ip or None,
                    required=True,
                    validator=v.Host(),
                ),
            ]
        return fields

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Teste la connexion SSH de chaque nœud et liste les échecs.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur par nœud en échec, ou None.
        """
        names = [n.name for n in ctx.data.get(DATA_NODES, [])]
        results = await asyncio.gather(*(self._check_node(ctx, name) for name in names))
        errors = [r for r in results if r]
        return " · ".join(errors) if errors else None

    async def _check_node(self, ctx: WizardContext, name: str) -> str | None:
        """Teste la connexion SSH d'un nœud.

        Args:
            ctx: Contexte de l'assistant.
            name: Nom du nœud.

        Returns:
            « nœud : raison » en cas d'échec, sinon None.
        """
        values = ctx.values
        prefix = f"nodes.{name}"
        try:
            await offload(
                self.checks.ssh.check,
                values[f"{prefix}.host"],
                values[f"{prefix}.user"],
                values[f"{prefix}.password"],
            )
        except CheckError as exc:
            return f"{name} : {exc}"
        return None

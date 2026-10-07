"""Page « Labs : WAN » : réseau des routeurs étudiants."""

from __future__ import annotations

from labomatics_cli.installer.pages.base import Page
from labomatics_cli.installer.pages.rules import AddressPool
from labomatics_cli.installer.pages.vm import bridge_options
from labomatics_cli.tui import ListField, SelectField, Step, TextField, WizardContext
from labomatics_cli.tui import validators as v


class WanPage(Page):
    """Interface, réseau, passerelle et exclusions du WAN étudiant."""

    title = "Labs : WAN"
    section = "wan"

    def build(self) -> Step:
        """Construit l'étape WAN.

        Returns:
            L'étape, dont `on_submit` vérifie qu'il reste des IP allouables.
        """
        fields = [
            SelectField(
                "Interface étudiants",
                bridge_options,
                key="wan.iface",
                required=True,
                helper="Bridge présent sur tous les nœuds",
            ),
            TextField(
                "Réseau WAN",
                key="wan.network",
                required=True,
                helper="Format x.x.x.x/xx",
                validator=v.AllOf(
                    v.Cidr(), v.NoOverlap("vxlan.network", "vm.admin_network")
                ),
            ),
            TextField(
                "Passerelle WAN",
                key="wan.gateway",
                required=True,
                validator=v.IpIn("wan.network"),
            ),
            ListField(
                "Exclusions",
                key="wan.exclusions",
                helper="10.210.0.2 ou 10.210.0.1-10.210.0.5",
                item_validator=v.AllOf(
                    v.IpOrRange(), v.IpIn("wan.network", exclude_edges=False)
                ),
            ),
        ]
        return Step(self.title, fields, on_submit=self._submit)

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Vérifie qu'il reste au moins une IP allouable.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur, ou None.
        """
        values = ctx.values
        pool = AddressPool(
            values["wan.network"],
            values["wan.gateway"],
            values.get("wan.exclusions", []),
        )
        if pool.free_count() < 1:
            return "Aucune IP allouable : réduis les exclusions ou agrandis le réseau"
        return None

"""Page « Labs : VXLAN » : zone SDN, réseau des labs et stockage partagé."""

from __future__ import annotations

from labomatics_cli.installer.pages.base import (
    DATA_API,
    DATA_STORAGES,
    Page,
    offload,
)
from labomatics_cli.installer.proxmox_api import ProxmoxError
from labomatics_cli.tui import (
    ConfirmField,
    SelectField,
    Step,
    TextField,
    WizardContext,
)
from labomatics_cli.tui import validators as v


def storage_options(ctx: WizardContext) -> list[tuple[str, str]]:
    """Options de stockages partagés.

    Args:
        ctx: Contexte de l'assistant (`ctx.data["storages"]`).

    Returns:
        Des couples (nom, libellé « nom (type) »).
    """
    return [(s.name, s.label) for s in ctx.data.get(DATA_STORAGES, [])]


def is_advanced(ctx: WizardContext) -> bool:
    """Indique si les paramètres avancés sont demandés.

    Args:
        ctx: Contexte de l'assistant.

    Returns:
        True si « Paramètres avancés » est coché.
    """
    return bool(ctx.values.get("vxlan.advanced"))


class VxlanPage(Page):
    """Zone VXLAN, réseau découpé en /24, stockage et paramètres avancés."""

    title = "Labs : VXLAN"
    section = "vxlan"

    def build(self) -> Step:
        """Construit l'étape VXLAN.

        Returns:
            L'étape, dont `on_submit` contrôle la zone SDN existante.
        """
        fields = [
            TextField(
                "Zone VXLAN",
                key="vxlan.zone",
                default="labo",
                required=True,
                helper="8 caractères maximum (limite Proxmox)",
                validator=v.Regex(
                    r"^[a-z][a-z0-9]{0,7}$",
                    "1 à 8 caractères : minuscules et chiffres, première lettre",
                ),
            ),
            TextField(
                "Réseau des labs",
                key="vxlan.network",
                default="10.96.0.0/12",
                required=True,
                helper="Découpé en /24 : chaque lab en reçoit un",
                validator=v.AllOf(
                    v.Cidr(max_prefix=23),
                    v.NoOverlap("vm.admin_network", "wan.network"),
                ),
            ),
            SelectField(
                "Stockage partagé",
                storage_options,
                key="vxlan.storage",
                required=True,
                helper="Partagé, contenu « images », présent sur tous les nœuds",
            ),
            ConfirmField("Paramètres avancés", key="vxlan.advanced", default=False),
            TextField(
                "VNI minimum",
                key="vxlan.vni_min",
                default=1000,
                required=True,
                visible_if=is_advanced,
                validator=v.IntRange(1, 16777215),
            ),
            TextField(
                "VNI maximum",
                key="vxlan.vni_max",
                default=4000,
                required=True,
                visible_if=is_advanced,
                validator=v.AllOf(
                    v.IntRange(1, 16777215), v.GreaterThan("vxlan.vni_min")
                ),
            ),
            TextField(
                "MTU",
                key="vxlan.mtu",
                default=1350,
                required=True,
                visible_if=is_advanced,
                helper="MTU physique − 50",
                validator=v.IntRange(576, 9000),
            ),
        ]
        return Step(
            self.title,
            fields,
            on_submit=self._submit,
            loading_text="Contrôle de la zone SDN…",
        )

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Accepte une zone absente ou de type vxlan, refuse un autre type.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur, ou None.
        """
        zone = ctx.values["vxlan.zone"]
        try:
            kind = await offload(ctx.data[DATA_API].sdn_zone, zone)
        except ProxmoxError as exc:
            return str(exc)
        if kind not in (None, "vxlan"):
            return f"La zone « {zone} » existe déjà avec le type « {kind} »"
        return None

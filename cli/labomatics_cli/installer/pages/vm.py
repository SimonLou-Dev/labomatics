"""Page « VM Labomatics » : domaine, réseau d'administration et paramètres de la VM."""

from __future__ import annotations

import ipaddress
from typing import Callable, Optional

from labomatics_cli.installer.checks import Checks
from labomatics_cli.installer.pages.base import DATA_BRIDGES, Page, offload
from labomatics_cli.installer.pages.fields import PrefillField
from labomatics_cli.installer.pages.rules import DifferentFrom
from labomatics_cli.installer.proxmox_api import Bridge
from labomatics_cli.tui import ListField, SelectField, Step, TextField, WizardContext
from labomatics_cli.tui import validators as v

IFACE_KEY = "vm.admin_iface"


def bridge_options(ctx: WizardContext) -> list[tuple[str, str]]:
    """Options de bridges communs à tous les nœuds.

    Args:
        ctx: Contexte de l'assistant (`ctx.data["bridges"]`).

    Returns:
        Des couples (nom, libellé « vmbr0 (10.0.0.1/24) »).
    """
    return [(b.name, b.label) for b in ctx.data.get(DATA_BRIDGES, [])]


def chosen_bridge(ctx: WizardContext, iface_key: str) -> Optional[Bridge]:
    """Bridge sélectionné dans le champ d'interface.

    Args:
        ctx: Contexte de l'assistant (`ctx.data["bridges"]`).
        iface_key: Clé du champ d'interface.

    Returns:
        Le bridge choisi, ou None.
    """
    chosen = ctx.values.get(iface_key)
    return next((b for b in ctx.data.get(DATA_BRIDGES, []) if b.name == chosen), None)


def iface_gateway(ctx: WizardContext, iface_key: str) -> Optional[str]:
    """Passerelle configurée sur l'interface choisie, si elle en a une.

    Args:
        ctx: Contexte de l'assistant.
        iface_key: Clé du champ d'interface.

    Returns:
        L'adresse de la passerelle, ou None.
    """
    bridge = chosen_bridge(ctx, iface_key)
    return bridge.gateway if bridge else None


def iface_network(ctx: WizardContext, iface_key: str) -> Optional[str]:
    """Réseau CIDR de l'interface choisie, si elle porte une IP.

    Args:
        ctx: Contexte de l'assistant.
        iface_key: Clé du champ d'interface.

    Returns:
        Le réseau (ex. « 10.100.25.0/24 »), ou None.
    """
    bridge = chosen_bridge(ctx, iface_key)
    if bridge is None or not bridge.cidr:
        return None
    return str(ipaddress.ip_network(bridge.cidr, strict=False))


class VmPage(Page):
    """Réseau d'administration et VM Labomatics."""

    title = "VM Labomatics"
    section = "vm"

    def __init__(
        self,
        checks: Optional[Checks] = None,
        ip_check_skipped: Callable[[], bool] = lambda: False,
    ) -> None:
        """Initialise la page.

        Args:
            checks: Contrôles réseau (ping), remplaçables en test.
            ip_check_skipped: Vrai quand la VM existe déjà et que son IP répond normalement.
        """
        self.checks = checks or Checks()
        self.ip_check_skipped = ip_check_skipped

    def build(self) -> Step:
        """Construit l'étape VM.

        Returns:
            L'étape, dont `on_submit` teste l'IP de la VM et la passerelle.
        """
        fields = [
            TextField(
                "Domaine",
                key="vm.domain",
                required=True,
                helper="Donne keycloak.<d>, labomatics.<d> et api.labomatics.<d>",
                validator=v.Domain(),
            ),
            SelectField(
                "Interface admin",
                bridge_options,
                key=IFACE_KEY,
                required=True,
                helper="Bridge présent sur tous les nœuds",
            ),
            PrefillField(
                "Réseau admin",
                key="vm.admin_network",
                suggest=lambda c: iface_network(c, IFACE_KEY),
                required=True,
                helper="Ex. 10.100.25.0/24",
                validator=v.Cidr(),
            ),
            PrefillField(
                "Passerelle admin",
                key="vm.admin_gateway",
                suggest=lambda c: iface_gateway(c, IFACE_KEY),
                required=True,
                validator=v.IpIn("vm.admin_network"),
            ),
            TextField(
                "IP de la VM",
                key="vm.vm_ip",
                required=True,
                helper="Adresse libre du réseau d'administration",
                validator=v.AllOf(
                    v.IpIn("vm.admin_network"),
                    DifferentFrom("vm.admin_gateway", "la passerelle"),
                ),
            ),
            ListField(
                "DNS amont",
                key="vm.dns_upstream",
                default=["1.1.1.1", "8.8.8.8"],
                required=True,
                helper="Résolution des domaines externes",
                item_validator=v.Ip(),
            ),
            ListField(
                "Clés SSH",
                key="vm.ssh_keys",
                helper="La clé du CLI est ajoutée automatiquement",
                item_validator=v.SshPublicKey(),
            ),
        ]
        return Step(
            self.title,
            fields,
            on_submit=self._submit,
            loading_text="Test des adresses…",
        )

    async def _submit(self, ctx: WizardContext) -> str | None:
        """Vérifie que l'IP de la VM est libre et que la passerelle répond.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Un message d'erreur, ou None si les adresses sont correctes.
        """
        ip, gateway = ctx.values["vm.vm_ip"], ctx.values["vm.admin_gateway"]
        if not self.ip_check_skipped() and await offload(self.checks.ping.is_alive, ip):
            return f"{ip} répond déjà au ping : l'IP de la VM doit être libre"
        if not await offload(self.checks.ping.is_alive, gateway):
            return f"La passerelle {gateway} ne répond pas depuis ce poste"
        return None

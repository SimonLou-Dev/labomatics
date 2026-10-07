"""Page « Reverse proxy » : proxies amont de confiance."""

from __future__ import annotations

from labomatics_cli.installer.pages.base import Page
from labomatics_cli.tui import ListField, Step
from labomatics_cli.tui import validators as v


class ProxyPage(Page):
    """Hôtes dont on accepte les en-têtes `X-Forwarded-*`."""

    title = "Reverse proxy"
    section = "proxy"

    def build(self) -> Step:
        """Construit l'étape du reverse proxy.

        Returns:
            L'étape avec la liste des hôtes de confiance.
        """
        fields = [
            ListField(
                "Hôtes de confiance",
                key="proxy.trusted_hosts",
                helper="Proxies amont dont on accepte les en-têtes X-Forwarded-*",
                item_validator=v.IpOrCidr(),
            )
        ]
        return Step(self.title, fields)

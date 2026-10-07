"""Rendu des templates Jinja2 de l'installeur."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined


class TemplateRenderer:
    """Rend les templates du paquet `labomatics_cli/templates` (variable manquante = erreur)."""

    def __init__(self) -> None:
        """Prépare l'environnement Jinja2."""
        self._env = Environment(
            loader=PackageLoader("labomatics_cli", "templates"),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def render(self, path: str, **context: Any) -> str:
        """Rend un template.

        Args:
            path: Chemin relatif au dossier des templates (ex. « dns/dnsmasq.conf.j2 »).
            **context: Variables du template.

        Returns:
            Le texte rendu.
        """
        return self._env.get_template(path).render(**context)

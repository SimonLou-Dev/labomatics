"""Socle commun des pages du wizard d'installation."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable

from labomatics_cli.models.install_config import InstallConfig
from labomatics_cli.tui import Step

DATA_API = "api"
DATA_NODES = "nodes"
DATA_BRIDGES = "bridges"
DATA_STORAGES = "storages"


class Page(ABC):
    """Page du wizard : construit un `Step` dont les clés sont `<section>.<champ>`."""

    title: str
    section: str

    @abstractmethod
    def build(self) -> Step:
        """Construit l'étape du wizard.

        Returns:
            L'étape avec ses champs et son éventuel `on_submit`.
        """

    def is_saved(self, config: InstallConfig) -> bool:
        """Indique si la page a déjà été validée et sauvegardée.

        Args:
            config: Configuration sauvegardée du cluster.

        Returns:
            True si la section de la page est renseignée.
        """
        return getattr(config, self.section) is not None


async def offload(func: Callable[..., Any], *args: Any) -> Any:
    """Exécute un appel bloquant (réseau) hors de la boucle d'événements.

    Args:
        func: Fonction bloquante.
        *args: Arguments de la fonction.

    Returns:
        Le résultat de la fonction.
    """
    return await asyncio.to_thread(func, *args)

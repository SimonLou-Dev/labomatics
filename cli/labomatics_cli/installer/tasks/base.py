"""Classe de base des tâches d'installation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from labomatics_cli.installer.context import InstallContext


class InstallTask(ABC):
    """Tâche idempotente : vérifie l'existant, met à jour ou ne fait rien."""

    name: str
    label: str
    skip_reason: str = "déjà en place"

    def is_needed(self, ctx: "InstallContext") -> bool:
        """Indique si la tâche doit s'exécuter.

        Args:
            ctx: Contexte d'installation.

        Returns:
            False pour que l'écran affiche la tâche comme ignorée.
        """
        return True

    @abstractmethod
    def run(self, ctx: "InstallContext") -> None:
        """Exécute la tâche (appelée dans un thread) et sauvegarde ses données.

        Args:
            ctx: Contexte d'installation.
        """


class PendingTask(InstallTask):
    """Tâche pas encore portée : toujours ignorée, jamais enregistrée comme faite."""

    skip_reason = "pas encore porté"

    def __init__(self, name: str, label: str) -> None:
        """Initialise la tâche provisoire.

        Args:
            name: Nom stable de la tâche.
            label: Libellé affiché.
        """
        self.name = name
        self.label = label

    def is_needed(self, ctx: "InstallContext") -> bool:
        """Indique que la tâche n'est jamais exécutée.

        Args:
            ctx: Contexte d'installation (inutilisé).

        Returns:
            Toujours False.
        """
        return False

    def run(self, ctx: "InstallContext") -> None:
        """Ne fait rien.

        Args:
            ctx: Contexte d'installation (inutilisé).
        """

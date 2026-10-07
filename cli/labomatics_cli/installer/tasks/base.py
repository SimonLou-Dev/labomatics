"""Classe de base des tâches d'installation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from labomatics_cli.installer.context import InstallContext


class InstallTask(ABC):
    """Tâche idempotente : vérifie l'existant, met à jour ou ne fait rien.

    Toutes les tâches sont exécutées à chaque installation. Une tâche dont
    `recorded` est faux n'est jamais enregistrée comme terminée dans l'état.
    """

    name: str
    label: str
    skip_reason: str = "déjà en place"
    recorded: bool = True

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

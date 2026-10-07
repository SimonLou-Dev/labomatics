"""Tâches d'installation et exécuteur injectable."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from labomatics_cli.installer.store import InstallStore
from labomatics_cli.tui import InstallReporter

INSTALL_TASKS: tuple[str, ...] = (
    "Token Labomatics",
    "Zone VXLAN",
    "VM Labomatics",
    "Docker",
    "DNS sur la VM",
    "DNS des nœuds Proxmox",
    "CA, templates et docker up",
    "Propagation des CA",
    "Keycloak",
    "Client Proxmox",
    "YAML d'init du backend",
    "Agent",
    "Contrôle de santé",
)

VM_TASK = INSTALL_TASKS[2]


class InstallRunner(ABC):
    """Exécute les 13 tâches d'installation pendant l'écran d'installation du wizard."""

    @abstractmethod
    async def run(
        self, store: InstallStore, values: Mapping[str, Any], ui: InstallReporter
    ) -> None:
        """Lance l'installation.

        Args:
            store: Store du cluster (config, secrets, tâches terminées).
            values: Valeurs finales du wizard, clés plates.
            ui: Rapporteur de l'écran d'installation.
        """


class PlaceholderRunner(InstallRunner):
    """Exécuteur provisoire : ignore chaque tâche en attendant leur portage."""

    async def run(
        self, store: InstallStore, values: Mapping[str, Any], ui: InstallReporter
    ) -> None:
        """Marque chaque tâche comme ignorée.

        Args:
            store: Store du cluster (inutilisé).
            values: Valeurs finales du wizard (inutilisées).
            ui: Rapporteur de l'écran d'installation.
        """
        for name in INSTALL_TASKS:
            ui.skip(name, "pas encore porté")

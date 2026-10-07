"""Tâche 12 : agent Proxmox (pas encore développé)."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask


class AgentTask(InstallTask):
    """Emplacement de l'agent : toujours ignoré tant qu'il n'existe pas."""

    name = "agent"
    label = "Agent"
    skip_reason = "agent pas encore développé"

    def is_needed(self, ctx: InstallContext) -> bool:
        """Indique que l'agent n'est jamais installé.

        Args:
            ctx: Contexte d'installation (inutilisé).

        Returns:
            Toujours False.
        """
        return False

    def run(self, ctx: InstallContext) -> None:
        """Ne fait rien.

        Args:
            ctx: Contexte d'installation (inutilisé).
        """

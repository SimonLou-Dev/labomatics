"""Exécuteur des tâches d'installation."""

from __future__ import annotations

import asyncio
from typing import Sequence

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask


class InstallError(Exception):
    """Échec d'une tâche d'installation, avec son libellé dans le message."""


class InstallRunner:
    """Exécute toutes les tâches dans l'ordre, depuis la première, à chaque passage.

    Les tâches sont idempotentes : chacune vérifie l'existant et ne refait que
    ce qui manque ou a changé.
    """

    def __init__(self, tasks: Sequence[InstallTask]) -> None:
        """Initialise l'exécuteur.

        Args:
            tasks: Tâches dans l'ordre d'exécution.
        """
        self.tasks = list(tasks)

    @property
    def labels(self) -> list[str]:
        """Libellés des tâches, tels qu'affichés à l'écran.

        Returns:
            Un libellé par tâche.
        """
        return [task.label for task in self.tasks]

    async def run(self, ctx: InstallContext) -> None:
        """Exécute toutes les tâches ; chaque tâche terminée est sauvegardée aussitôt.

        Une tâche ignorée n'est pas enregistrée comme terminée.

        Args:
            ctx: Contexte d'installation.

        Raises:
            InstallError: Si une tâche échoue (l'échec est aussi enregistré dans le store).
        """
        store, ui = ctx.store, ctx.ui
        store.mark_in_progress()
        try:
            for task in self.tasks:
                ui.step(task.label)
                try:
                    if not await asyncio.to_thread(task.is_needed, ctx):
                        ui.skip(task.label, task.skip_reason)
                        continue
                    await asyncio.to_thread(task.run, ctx)
                except Exception as exc:
                    message = f"{task.label} : {exc}"
                    store.mark_failed(message)
                    raise InstallError(message) from exc
                if task.recorded:
                    store.mark_task_done(task.name)
            store.mark_completed()
        finally:
            ctx.close()

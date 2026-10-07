"""Exécuteur des tâches d'installation."""

from __future__ import annotations

import asyncio
from typing import Collection, Sequence

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask


class InstallError(Exception):
    """Échec d'une tâche d'installation, avec son libellé dans le message."""


class InstallRunner:
    """Exécute les tâches dans l'ordre, en reprenant après la dernière tâche terminée."""

    def __init__(
        self, tasks: Sequence[InstallTask], rerun: Collection[str] = ()
    ) -> None:
        """Initialise l'exécuteur.

        Args:
            tasks: Tâches dans l'ordre d'exécution.
            rerun: Noms des tâches à rejouer même si elles sont déjà terminées.
        """
        self.tasks = list(tasks)
        self.rerun = set(rerun)

    @property
    def labels(self) -> list[str]:
        """Libellés des tâches, tels qu'affichés à l'écran.

        Returns:
            Un libellé par tâche.
        """
        return [task.label for task in self.tasks]

    async def run(self, ctx: InstallContext) -> None:
        """Exécute les tâches ; chaque tâche terminée est sauvegardée aussitôt.

        Une tâche ignorée n'est pas enregistrée comme terminée : elle est
        réévaluée à chaque passage. Les tâches à rejouer sont oubliées d'abord,
        pour qu'une reprise après échec les rejoue aussi.

        Args:
            ctx: Contexte d'installation.

        Raises:
            InstallError: Si une tâche échoue (l'échec est aussi enregistré dans le store).
        """
        store, ui = ctx.store, ctx.ui
        store.mark_in_progress()
        store.forget_tasks(self.rerun)
        try:
            for task in self.tasks:
                if store.is_task_done(task.name) and task.name not in self.rerun:
                    ui.mark_done(task.label)
                    continue
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

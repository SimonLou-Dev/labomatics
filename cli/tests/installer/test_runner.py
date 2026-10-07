import asyncio

import pytest

from labomatics_cli.installer.runner import InstallError, InstallRunner
from labomatics_cli.installer.store import InstallStatus
from labomatics_cli.installer.tasks import build_tasks
from labomatics_cli.installer.tasks.base import InstallTask
from labomatics_cli.tui import InstallReporter
from task_fakes import make_ctx


class FakeTask(InstallTask):
    """Tâche factice qui note ses exécutions dans `log`."""

    def __init__(self, name, log, needed=True, fail=False):
        """Initialise la tâche.

        Args:
            name: Nom (et libellé) de la tâche.
            log: Liste partagée recevant le nom à chaque exécution.
            needed: Valeur de `is_needed`.
            fail: Lève une erreur si vrai.
        """
        self.name = self.label = name
        self.log, self.needed, self.fail = log, needed, fail

    def is_needed(self, ctx):
        """Renvoie le choix configuré.

        Args:
            ctx: Contexte.

        Returns:
            La valeur configurée.
        """
        return self.needed

    def run(self, ctx):
        """Note l'exécution, ou échoue.

        Args:
            ctx: Contexte.

        Raises:
            RuntimeError: Si la tâche est configurée pour échouer.
        """
        self.log.append(self.name)
        if self.fail:
            raise RuntimeError("boum")


def prepare(tmp_path, tasks, rerun=()):
    """Prépare contexte et rapporteur pour un runner de fausses tâches."""
    ctx = make_ctx(tmp_path)
    ctx.ui = InstallReporter([t.label for t in tasks])
    return ctx, InstallRunner(tasks, rerun)


def test_runs_all_tasks_and_saves_each(tmp_path):
    """Chaque tâche est enregistrée, puis l'installation est marquée terminée."""
    log = []
    tasks = [FakeTask("a", log), FakeTask("b", log)]
    ctx, runner = prepare(tmp_path, tasks)
    asyncio.run(runner.run(ctx))
    assert log == ["a", "b"]
    assert ctx.store.completed_tasks == ["a", "b"]
    assert ctx.store.status == InstallStatus.completed and ctx.store.is_installed


def test_failure_stops_and_resume_skips_done(tmp_path):
    """Un échec s'enregistre et stoppe ; la reprise saute les tâches terminées."""
    log = []
    tasks = [FakeTask("a", log), FakeTask("b", log, fail=True), FakeTask("c", log)]
    ctx, runner = prepare(tmp_path, tasks)
    with pytest.raises(InstallError, match="b : boum"):
        asyncio.run(runner.run(ctx))
    assert log == ["a", "b"] and ctx.store.completed_tasks == ["a"]
    assert ctx.store.status == InstallStatus.failed
    assert "boum" in ctx.store.last_error
    tasks[1].fail = False
    ctx2, runner2 = prepare(tmp_path, tasks)
    asyncio.run(runner2.run(ctx2))
    assert log == ["a", "b", "b", "c"]
    assert ctx2.ui.status[:2] == ["done", "done"] and ctx2.store.is_installed


def test_skipped_task_is_not_recorded(tmp_path):
    """Une tâche inutile est affichée ignorée et réévaluée à la prochaine exécution."""
    log = []
    ctx, runner = prepare(tmp_path, [FakeTask("a", log, needed=False)])
    asyncio.run(runner.run(ctx))
    assert log == [] and ctx.ui.status == ["skipped"]
    assert ctx.store.completed_tasks == []


def test_rerun_replays_done_tasks(tmp_path):
    """Les tâches de `rerun` sont rejouées même si elles sont terminées."""
    log = []
    tasks = [FakeTask("a", log), FakeTask("b", log)]
    ctx, runner = prepare(tmp_path, tasks)
    asyncio.run(runner.run(ctx))
    ctx2, runner2 = prepare(tmp_path, tasks, rerun={"b"})
    asyncio.run(runner2.run(ctx2))
    assert log == ["a", "b", "b"]


def test_default_tasks_names_and_pending_skipped(tmp_path):
    """Les 13 tâches ont un nom stable ; les tâches 7 à 13 sont ignorées sans être enregistrées."""
    tasks = build_tasks()
    assert [t.name for t in tasks] == [
        "token",
        "sdn",
        "vm",
        "docker",
        "dns",
        "node_dns",
        "stack",
        "ca_propagation",
        "keycloak",
        "proxmox_oidc",
        "backend",
        "agent",
        "health",
    ]
    ctx, _ = prepare(tmp_path, tasks)
    runner = InstallRunner(tasks[6:])
    ctx.ui = InstallReporter(runner.labels)
    asyncio.run(runner.run(ctx))
    assert set(ctx.ui.status) == {"skipped"} and ctx.store.completed_tasks == []

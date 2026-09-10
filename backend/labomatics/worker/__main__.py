"""Entrée CLI : démarre le worker Celery Scheduler (+ optionnellement Beat)."""

import subprocess
import sys


def run() -> None:
    """Lance celery worker sur la queue 'scheduler'."""
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "celery",
            "-A",
            "labomatics.worker.broker",
            "worker",
            "--loglevel=info",
            "-c",
            "2",
            "-n",
            "scheduler@%h",
        ],
        check=True,
    )


def run_beat() -> None:
    """Lance Celery Beat (planificateur des tâches périodiques)."""
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "celery",
            "-A",
            "labomatics.worker.broker",
            "beat",
            "--loglevel=info",
            "--scheduler",
            "celery.beat.PersistentScheduler",
        ],
        check=True,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "beat":
        run_beat()
    else:
        run()

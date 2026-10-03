"""Pont taches Celery <-> code async + emission d'evenements de progression.

Les taches Celery sont synchrones et tournent dans un process worker isole ;
`run_async` execute la logique metier async (services/repos) dans une boucle
dediee. `emit` publie la progression sur le canal Redis `job:{job_id}`, relaye
au front par `/ws/jobs/{job_id}` (voir `kitcat/api/routes/v1/ws.py`).

Format d'evenement : {type, step?, message?, ...extra}
type ∈ step_start | step_done | step_error | done | error
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from labomatics.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
notification_service = NotificationService()


def new_job_id() -> str:
    """Identifiant de job (UUID) pour l'abonnement WS cote front."""
    return uuid4().hex


def run_async(coro) -> Any:
    """Execute une coroutine dans une boucle dediee (contexte worker sync)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


async def emit(
    job_id: str | None,
    event_type: str,
    *,
    step: str | None = None,
    message: str | None = None,
    task_id: str | None = None,
    **extra: Any,
) -> None:
    """Publie un evenement de progression (no-op sans job_id, best-effort).

    Enregistre aussi les updates dans Redis pour le tracking des tâches.
    """
    if not job_id:
        return
    event: dict[str, Any] = {"type": event_type}
    if step is not None:
        event["step"] = step
    if message is not None:
        event["message"] = message
    event.update(extra)
    await notification_service.publish_job_event(job_id, event)

    # Enregistrer aussi dans Redis pour le tracking (best-effort)
    if task_id and isinstance(task_id, str) and task_id.strip():
        try:
            from labomatics.services.task_tracking_service import TaskTrackingService
            task_service = TaskTrackingService()

            if event_type == "step_start":
                await task_service.update_step(task_id, job_id, step or "", "running")
            elif event_type == "step_done":
                await task_service.update_step(task_id, job_id, step or "", "done")
            elif event_type == "step_error":
                await task_service.update_step(task_id, job_id, step or "", "error", message)
            elif event_type == "done":
                await task_service.complete_task(task_id, "completed")
            elif event_type == "error":
                await task_service.complete_task(task_id, "error", message)
        except Exception as e:
            logger.warning(f"Failed to track task in Redis: {e}")

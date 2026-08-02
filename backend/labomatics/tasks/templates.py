"""Tâches pour les templates OpenWRT."""

from __future__ import annotations

import logging

from labomatics.services import get_cluster_service, get_proxmox_service
from labomatics.services.notification_service import NotificationService
from labomatics.worker.broker import celery_app
from labomatics.worker.jobs import run_async

cluster_service = get_cluster_service()
proxmox_service = get_proxmox_service()
logger = logging.getLogger(__name__)
notification_service = NotificationService()


async def _templates(job_id: str | None = None) -> None:
    """Crée la template OpenWRT (TODO)."""
    logger.info("Template build task (TODO)")


@celery_app.task(name="labomatics.templates")
def templates(job_id: str | None = None) -> None:
    """Lance la création de template."""
    run_async(_templates(job_id))

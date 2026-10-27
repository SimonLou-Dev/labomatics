"""Application Celery KitCAT (broker/backend Redis)."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from labomatics.core.config.settings import settings

celery_app = Celery(
    "labomatics",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=[
        "labomatics.tasks.students",
        "labomatics.tasks.lab",
        "labomatics.tasks.security_check",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_default_queue=f"labomatics-{settings.environment}.default",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    timezone=settings.time_zone,
    beat_schedule={
        "daily-security-check": {
            "task": "labomatics.daily_security_check",
            # Heure creuse ; nécessite un processus `celery beat` en déploiement.
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

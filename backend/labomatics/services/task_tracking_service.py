"""Service pour tracker les tâches en temps réel avec Redis."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import redis

logger = logging.getLogger(__name__)


class TaskTrackingService:
    """Gère le tracking des tâches en Redis."""

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self.redis = redis_client or redis.Redis(
            host="localhost", port=6379, db=0, decode_responses=True
        )
        self.task_ttl = 60  # Garde les tâches terminées 60 secondes

    async def create_task(
        self,
        task_id: str,
        user_id: str | UUID | None,
        task_type: str,
        description: str = "",
    ) -> None:
        """Crée une nouvelle tâche."""
        task_data = {
            "id": task_id,
            "user_id": str(user_id) if user_id else "",
            "type": task_type,
            "description": description,
            "status": "in_progress",
            "created_at": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": "",
            "error": "",
            "steps": "[]",
            "current_step": "",
            "jobs": "{}",
        }
        self.redis.hset(f"task:{task_id}", mapping=task_data)
        self.redis.rpush("tasks:current", task_id)
        if user_id:
            self.redis.rpush(f"user_tasks:{str(user_id)}", task_id)

    async def add_job(self, task_id: str, job_id: str, description: str = "") -> None:
        """Ajoute un job à une tâche."""
        job_data = {
            "id": job_id,
            "description": description,
            "status": "pending",
            "total_steps": 0,
            "completed_steps": 0,
            "error": "",
        }
        self.redis.hset(f"task:{task_id}:job:{job_id}", mapping=job_data)

    async def update_job_steps(
        self, task_id: str, job_id: str, steps: list[str]
    ) -> None:
        """Met à jour les steps d'un job."""
        self.redis.hset(
            f"task:{task_id}:job:{job_id}",
            mapping={
                "total_steps": len(steps),
                "status": "running",
                "steps": json.dumps(steps),
            },
        )

    async def update_step(
        self,
        task_id: str,
        job_id: str,
        step: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Met à jour le statut d'une step."""
        if status == "done":
            current_jobs = self.redis.hgetall(f"task:{task_id}:job:{job_id}")
            completed = int(current_jobs.get("completed_steps", 0)) + 1
            self.redis.hset(
                f"task:{task_id}:job:{job_id}",
                mapping={"completed_steps": completed, "current_step": step},
            )
        elif status == "error":
            self.redis.hset(
                f"task:{task_id}:job:{job_id}",
                mapping={"error": error, "status": "error"},
            )

    async def complete_task(
        self, task_id: str, status: str = "completed", error: str | None = None
    ) -> None:
        """Marque une tâche comme terminée."""
        completed_at = datetime.utcnow().isoformat()
        self.redis.hset(
            f"task:{task_id}",
            mapping={
                "status": status,
                "completed_at": completed_at,
                "error": error or "",
            },
        )
        self.redis.lrem("tasks:current", 0, task_id)

        if status == "completed":
            self.redis.rpush("tasks:recent", task_id)
            self.redis.expire(f"task:{task_id}", self.task_ttl)
        elif status == "error":
            self.redis.rpush("tasks:errors", task_id)
            self.redis.expire(f"task:{task_id}", self.task_ttl * 5)

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Récupère les détails d'une tâche."""
        task_data = self.redis.hgetall(f"task:{task_id}")
        if not task_data:
            return None

        # Récupérer les jobs associés
        jobs = {}
        for key in self.redis.keys(f"task:{task_id}:job:*"):
            job_id = key.split(":")[-1]
            job_data = self.redis.hgetall(f"task:{task_id}:job:{job_id}")
            if job_data.get("steps"):
                job_data["steps"] = json.loads(job_data["steps"])
            jobs[job_id] = job_data

        task_data["jobs"] = jobs
        return task_data

    async def get_all_tasks(self, user_id: str | None = None) -> dict[str, Any]:
        """Récupère toutes les tâches (actuelles, récentes, erreurs)."""
        tasks = {
            "in_progress": [],
            "completed_recent": [],
            "errors": [],
        }

        # Tâches en cours
        current_ids = self.redis.lrange("tasks:current", 0, -1)
        for task_id in current_ids:
            if user_id is None or self._is_user_task(task_id, user_id):
                task = await self.get_task(task_id)
                if task:
                    tasks["in_progress"].append(task)

        # Tâches récemment terminées
        recent_ids = self.redis.lrange("tasks:recent", 0, -1)
        for task_id in recent_ids:
            if user_id is None or self._is_user_task(task_id, user_id):
                task = await self.get_task(task_id)
                if task:
                    tasks["completed_recent"].append(task)

        # Tâches en erreur
        error_ids = self.redis.lrange("tasks:errors", 0, -1)
        for task_id in error_ids:
            if user_id is None or self._is_user_task(task_id, user_id):
                task = await self.get_task(task_id)
                if task:
                    tasks["errors"].append(task)

        return tasks

    def _is_user_task(self, task_id: str, user_id: str) -> bool:
        """Vérifie si une tâche appartient à l'utilisateur."""
        task_data = self.redis.hgetall(f"task:{task_id}")
        stored_user_id = task_data.get("user_id", "")
        return stored_user_id == str(user_id)

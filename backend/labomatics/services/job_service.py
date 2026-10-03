import logging
from datetime import datetime
from labomatics.api.dto.notification import JobDTO
from labomatics.api.dto.student import StudentImportDiffDTO
from labomatics.tasks import students as student_tasks
from labomatics.worker.jobs import new_job_id
from labomatics.services.task_tracking_service import TaskTrackingService

logger = logging.getLogger(__name__)


class JobService:
    """Service d'orchestration des taches asynchrones avec tracking Redis."""

    @staticmethod
    def _start_task(task_id: str, user_id: str | None, task_type: str, description: str) -> None:
        """Crée une tâche dans Redis (synchrone, fire and forget)."""
        try:
            task_service = TaskTrackingService()
            # Appel synchrone seulement avec des valeurs non-None
            now = datetime.utcnow().isoformat()
            task_service.redis.hset(f"task:{task_id}", mapping={
                "id": task_id,
                "user_id": str(user_id) if user_id else "",
                "type": task_type,
                "description": description,
                "status": "in_progress",
                "created_at": now,
                "started_at": now,
                "completed_at": "",
                "error": "",
            })
            task_service.redis.rpush("tasks:current", task_id)
            if user_id:
                task_service.redis.rpush(f"user_tasks:{str(user_id)}", task_id)
        except Exception as e:
            logger.warning(f"Failed to create task in Redis: {e}")

    @staticmethod
    def enqueue_apply_students(students: StudentImportDiffDTO, user_id: str | None = None) -> list[JobDTO]:
        """Met en file l'import d'étudiants avec tracking Redis."""
        # Convertir les DTOs en dicts pour la sérialisation Celery
        modified_dicts = [s.model_dump() for s in students.modified]
        added_dicts = [s.model_dump() for s in students.added]
        deleted_dicts = [s.model_dump() for s in students.deleted]

        # Créer une tâche principale
        task_id = new_job_id()
        JobService._start_task(task_id, user_id, "student_import", "Import d'étudiants")

        # Enqueuer les 3 jobs avec tracking
        update_job_id = new_job_id()
        student_tasks.update_students.delay(modified_dicts, job_id=update_job_id, task_id=task_id)

        create_job_id = new_job_id()
        student_tasks.create_students.delay(added_dicts, job_id=create_job_id, task_id=task_id)

        delete_job_id = new_job_id()
        student_tasks.delete_students.delay(deleted_dicts, job_id=delete_job_id, task_id=task_id)

        return [
            JobDTO(jobId=update_job_id),
            JobDTO(jobId=create_job_id),
            JobDTO(jobId=delete_job_id),
        ]

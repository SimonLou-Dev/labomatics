from labomatics.api.dto.notification import JobDTO
from labomatics.api.dto.student import StudentImportDiffDTO
from labomatics.tasks import students as student_tasks
from labomatics.worker.jobs import new_job_id


class JobService:
    """Service d'orchestration des taches asynchrones."""

    def __init__(self) -> None:
        """Constructeur."""
        pass

    @staticmethod
    def enqueue_apply_students(students: StudentImportDiffDTO) -> list[JobDTO]:
        """Met en file le build (ATLAS) de l'archive d'une release."""
        # Convertir les DTOs en dicts pour la sérialisation Celery
        modified_dicts = [s.model_dump() for s in students.modified]
        added_dicts = [s.model_dump() for s in students.added]
        deleted_dicts = [s.model_dump() for s in students.deleted]

        update_job_id = new_job_id()
        student_tasks.update_students.delay(modified_dicts)
        create_job_id = new_job_id()
        student_tasks.create_students.delay(added_dicts)
        delete_job_id = new_job_id()
        student_tasks.delete_students.delay(deleted_dicts)

        return [
            JobDTO(jobId=update_job_id),
            JobDTO(jobId=create_job_id),
            JobDTO(jobId=delete_job_id),
        ]

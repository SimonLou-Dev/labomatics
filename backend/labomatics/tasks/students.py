from __future__ import annotations

import logging

from labomatics.api.dto.student import StudentImportItemDTO
from labomatics.services import StudentService, get_student_service
from labomatics.services.notification_service import NotificationService
from labomatics.worker.broker import celery_app
from labomatics.worker.jobs import run_async

student_service: StudentService = get_student_service()
logger = logging.getLogger(__name__)
notification_service = NotificationService()


async def _update_student(
    students_data: list[dict],
    job_id: str | None = None,
    task_id: str | None = None,
    user_id: str | None = None,
) -> None:
    try:
        for student_dict in students_data:
            student = StudentImportItemDTO(**student_dict)
            await student_service.update_student(data=student)

        if job_id:
            from labomatics.worker.jobs import emit

            await emit(job_id, "done", task_id=task_id, message="Mise à jour terminée")
    except Exception as e:
        if job_id:
            from labomatics.worker.jobs import emit

            await emit(job_id, "error", task_id=task_id, message=str(e))
        raise


@celery_app.task(name="labomatics.update_students")
def update_students(
    students_data: list[dict],
    job_id: str | None = None,
    task_id: str | None = None,
    user_id: str | None = None,
) -> None:
    run_async(_update_student(students_data, job_id, task_id, user_id))


async def _delete_students(
    students_data: list[dict],
    job_id: str | None = None,
    task_id: str | None = None,
    user_id: str | None = None,
) -> None:
    try:
        for student_dict in students_data:
            student = StudentImportItemDTO(**student_dict)
            await student_service.delete_student(data=student)

        if job_id:
            from labomatics.worker.jobs import emit

            await emit(job_id, "done", task_id=task_id, message="Suppression terminée")
    except Exception as e:
        if job_id:
            from labomatics.worker.jobs import emit

            await emit(job_id, "error", task_id=task_id, message=str(e))
        raise


@celery_app.task(name="labomatics.delete_students")
def delete_students(
    students_data: list[dict],
    job_id: str | None = None,
    task_id: str | None = None,
    user_id: str | None = None,
) -> None:
    run_async(_delete_students(students_data, job_id, task_id, user_id))


async def _create_students(
    students_data: list[dict],
    job_id: str | None = None,
    task_id: str | None = None,
    user_id: str | None = None,
) -> None:
    try:
        # Un étudiant en échec ne bloque pas les suivants, mais il est signalé :
        # `create_student` l'a déjà retiré de la base, le prochain import le
        # recréera (#85).
        failed: list[str] = []
        for student_dict in students_data:
            student = StudentImportItemDTO(**student_dict)
            try:
                await student_service.create_student(data=student)
            except Exception as e:
                logger.error(f"Création de l'étudiant {student.id} échouée: {e}")
                failed.append(f"{student.first_name} {student.last_name}")

        if job_id:
            from labomatics.worker.jobs import emit

            if failed:
                await emit(
                    job_id,
                    "error",
                    task_id=task_id,
                    message=(
                        f"{len(failed)}/{len(students_data)} étudiant(s) non créé(s), "
                        f"à réimporter : {', '.join(failed)}"
                    ),
                    failed=failed,
                )
            else:
                await emit(job_id, "done", task_id=task_id, message="Création terminée")
    except Exception as e:
        if job_id:
            from labomatics.worker.jobs import emit

            await emit(job_id, "error", task_id=task_id, message=str(e))
        raise


@celery_app.task(name="labomatics.create_students")
def create_students(
    students_data: list[dict],
    job_id: str | None = None,
    task_id: str | None = None,
    user_id: str | None = None,
) -> None:
    run_async(_create_students(students_data, job_id, task_id, user_id))

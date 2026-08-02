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
    students_data: list[dict], job_id: str | None = None, user_id: str | None = None
) -> None:
    for student_dict in students_data:
        student = StudentImportItemDTO(**student_dict)
        await student_service.update_student(data=student)

    # TODO: send notification


@celery_app.task(name="labomatics.update_students")
def update_students(
    students_data: list[dict], job_id: str | None = None, user_id: str | None = None
) -> None:
    run_async(_update_student(students_data, job_id, user_id))


async def _delete_students(
    students_data: list[dict], job_id: str | None = None, user_id: str | None = None
) -> None:
    for student_dict in students_data:
        student = StudentImportItemDTO(**student_dict)
        await student_service.delete_student(data=student)

    # TODO: send notification


@celery_app.task(name="labomatics.delete_students")
def delete_students(
    students_data: list[dict], job_id: str | None = None, user_id: str | None = None
) -> None:
    run_async(_delete_students(students_data, job_id, user_id))


async def _create_students(
    students_data: list[dict], job_id: str | None = None, user_id: str | None = None
) -> None:
    for student_dict in students_data:
        student = StudentImportItemDTO(**student_dict)
        await student_service.create_student(data=student)

    # TODO: send notification


@celery_app.task(name="labomatics.create_students")
def create_students(
    students_data: list[dict], job_id: str | None = None, user_id: str | None = None
) -> None:
    run_async(_create_students(students_data, job_id, user_id))

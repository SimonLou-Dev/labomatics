"""Création d'étudiant : mot de passe atomique et absence d'orphelins (#85).

Keycloak et le mail sont injectés (fakes partagés avec `test_teacher_service`).
"""

from __future__ import annotations

import random
import uuid

import pytest

from labomatics.api.dto.student import StudentImportItemDTO
from labomatics.core.db.repository.student import StudentRepository
from labomatics.services.student_service import StudentService
from labomatics.tasks import students as student_tasks
from labomatics.utils.login_helper import DEFAULT_PASSWORD_LENGTH
from tests.test_teacher_service import _FakeKeycloakService, _FakeMailService


def _student_data(cohort_name: str | None = None) -> StudentImportItemDTO:
    suffix = uuid.uuid4().hex[:8]
    return StudentImportItemDTO(
        # external_id est un entier unique : tirage large pour éviter les collisions
        id=str(random.randint(10**8, 10**9)),  # noqa: S311
        first_name="Alice",
        last_name=f"Durand{suffix}",
        email=f"alice.durand-{suffix}@test.local",
        cohort_name=cohort_name,
    )


async def test_create_student_sends_policy_password_with_account():
    keycloak = _FakeKeycloakService()
    mail = _FakeMailService()
    service = StudentService(keycloak_service=keycloak, mail_service=mail)
    data = _student_data()

    await service.create_student(data)

    create_call = keycloak.called("create_user")[0]
    assert len(create_call["password"]) == DEFAULT_PASSWORD_LENGTH
    assert create_call["temporary"] is True
    assert keycloak.called("set_user_password") == []
    assert mail.sent[0]["context"]["password"] == create_call["password"]

    student = await StudentRepository().get_by_external_id(int(data.id))
    assert student is not None
    assert student.keycloak_user_id == uuid.UUID(keycloak.created_id)


async def test_create_student_keycloak_failure_removes_db_row():
    """Le compte Keycloak n'existe pas : seul l'étudiant en base est annulé."""
    keycloak = _FakeKeycloakService(fail=True)
    service = StudentService(keycloak_service=keycloak, mail_service=_FakeMailService())
    data = _student_data()

    with pytest.raises(RuntimeError):
        await service.create_student(data)

    assert await StudentRepository().get_by_external_id(int(data.id)) is None
    assert keycloak.called("delete_user") == []


@pytest.mark.parametrize(
    ("keycloak_fail_on", "mail_fail"),
    [({"add_user_to_group"}, False), (set(), True)],
    ids=["group_assignment_fails", "mail_fails"],
)
async def test_create_student_failure_after_keycloak_rolls_everything_back(
    keycloak_fail_on, mail_fail
):
    keycloak = _FakeKeycloakService(fail_on=keycloak_fail_on)
    service = StudentService(
        keycloak_service=keycloak, mail_service=_FakeMailService(fail=mail_fail)
    )
    data = _student_data(cohort_name=f"student-test-{uuid.uuid4().hex[:8]}")

    with pytest.raises(RuntimeError):
        await service.create_student(data)

    # Étudiant et enrollment supprimés (sinon la FK RESTRICT bloquerait le delete)
    assert await StudentRepository().get_by_external_id(int(data.id)) is None
    login = keycloak.called("create_user")[0]["login"]
    assert keycloak.called("delete_user") == [{"login": login}]


async def test_create_students_task_reports_failures_and_continues(monkeypatch):
    """Un échec n'interrompt pas l'import mais est remonté dans l'événement final."""
    ok, ko = _student_data(), _student_data()
    created: list[str] = []

    async def fake_create_student(data: StudentImportItemDTO) -> None:
        if data.id == ko.id:
            raise RuntimeError("keycloak down")
        created.append(data.id)

    events: list[dict] = []

    async def fake_emit(job_id, event_type, **kwargs):
        events.append({"type": event_type, **kwargs})

    monkeypatch.setattr(
        student_tasks.student_service, "create_student", fake_create_student
    )
    monkeypatch.setattr("labomatics.worker.jobs.emit", fake_emit)

    await student_tasks._create_students(
        [ko.model_dump(), ok.model_dump()], job_id="job", task_id="task"
    )

    assert created == [ok.id]
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert events[0]["failed"] == [f"{ko.first_name} {ko.last_name}"]
    assert "1/2" in events[0]["message"]


async def test_create_students_task_done_when_all_succeed(monkeypatch):
    async def fake_create_student(data: StudentImportItemDTO) -> None:
        return None

    events: list[dict] = []

    async def fake_emit(job_id, event_type, **kwargs):
        events.append({"type": event_type, **kwargs})

    monkeypatch.setattr(
        student_tasks.student_service, "create_student", fake_create_student
    )
    monkeypatch.setattr("labomatics.worker.jobs.emit", fake_emit)

    await student_tasks._create_students(
        [_student_data().model_dump()], job_id="job", task_id="task"
    )

    assert [e["type"] for e in events] == ["done"]

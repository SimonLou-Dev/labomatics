"""Tests unitaires — TeacherService (#58).

Keycloak et le mail sont mockés via injection (pattern déjà utilisé par
`StudentService`), donc ces tests ne dépendent pas d'un Keycloak réel.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from labomatics.api.dto.teacher import TeacherCreateDTO, TeacherUpdateDTO
from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.models.enrollment import Enrollment
from labomatics.core.db.models.student import Student
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.enrollment import EnrollmentRepository
from labomatics.core.db.repository.student import StudentRepository
from labomatics.core.db.repository.teacher import TeacherRepository
from labomatics.core.db.repository.teacher_cohort import TeacherCohortRepository
from labomatics.services.teacher_service import TeacherService


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


class _FakeKeycloakService:
    def __init__(
        self, *, fail: bool = False, existing_users: dict | None = None
    ) -> None:
        self.fail = fail
        self.calls: list[tuple[str, dict]] = []
        self.existing_users = existing_users or {}

    async def create_user(self, **kwargs):
        self.calls.append(("create_user", kwargs))
        if self.fail:
            raise RuntimeError("keycloak unreachable")
        return {"id": str(uuid.uuid4())}

    async def update_user(self, **kwargs):
        self.calls.append(("update_user", kwargs))

    async def add_user_to_group(self, **kwargs):
        self.calls.append(("add_user_to_group", kwargs))

    async def set_user_password(self, **kwargs):
        self.calls.append(("set_user_password", kwargs))

    async def delete_user(self, **kwargs):
        self.calls.append(("delete_user", kwargs))

    async def get_user_by_login(self, login: str):
        self.calls.append(("get_user_by_login", {"login": login}))
        return self.existing_users.get(login)


class _FakeMailService:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_templated_mail(self, **kwargs):
        self.sent.append(kwargs)


@pytest.fixture
async def seeded_cohort():
    repo = CohortRepository()
    now = datetime.now(UTC).replace(tzinfo=None)
    cohort = await repo.add(
        Cohort(
            name=f"teacher-test-{_suffix()}",
            year=2026,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=300),
        )
    )
    yield cohort


async def test_create_teacher_persists_db_and_assigns_cohorts(seeded_cohort):
    keycloak = _FakeKeycloakService()
    mail = _FakeMailService()
    service = TeacherService(keycloak_service=keycloak, mail_service=mail)

    data = TeacherCreateDTO(
        first_name="Jean",
        last_name="Martin",
        email=f"jean.martin-{_suffix()}@test.local",
        cohort_ids=[str(seeded_cohort.id)],
    )
    result = await service.create_teacher(data)

    assert result.first_name == "Jean"
    assert result.cohort_names == [seeded_cohort.name]

    teacher_cohort_repo = TeacherCohortRepository()
    teacher_cohorts = await teacher_cohort_repo.list_by_teacher_id(uuid.UUID(result.id))
    assert len(teacher_cohorts) == 1
    assert teacher_cohorts[0].cohort_id == seeded_cohort.id

    group_calls = [c for c in keycloak.calls if c[0] == "add_user_to_group"]
    assert group_calls[0][1]["group_name"] == "prof"
    assert len(mail.sent) == 1


async def test_create_teacher_with_unknown_cohort_id_raises_404():
    service = TeacherService(
        keycloak_service=_FakeKeycloakService(), mail_service=_FakeMailService()
    )
    data = TeacherCreateDTO(
        first_name="Jean",
        last_name="Martin",
        email=f"jean.martin-{_suffix()}@test.local",
        cohort_ids=[str(uuid.uuid4())],
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_teacher(data)
    assert exc_info.value.status_code == 404

    teacher_repo = TeacherRepository()
    assert await teacher_repo.get_by_email(data.email) is None


async def test_create_teacher_propagates_keycloak_failure(seeded_cohort):
    """Contrairement à `create_student`, l'échec Keycloak n'est pas avalé."""
    service = TeacherService(
        keycloak_service=_FakeKeycloakService(fail=True),
        mail_service=_FakeMailService(),
    )
    data = TeacherCreateDTO(
        first_name="Jean",
        last_name="Martin",
        email=f"jean.martin-{_suffix()}@test.local",
        cohort_ids=[str(seeded_cohort.id)],
    )
    with pytest.raises(RuntimeError):
        await service.create_teacher(data)


async def test_update_teacher_resyncs_cohorts(seeded_cohort):
    keycloak = _FakeKeycloakService()
    service = TeacherService(keycloak_service=keycloak, mail_service=_FakeMailService())

    created = await service.create_teacher(
        TeacherCreateDTO(
            first_name="Jean",
            last_name="Martin",
            email=f"jean.martin-{_suffix()}@test.local",
            cohort_ids=[str(seeded_cohort.id)],
        )
    )

    other_cohort = await CohortRepository().add(
        Cohort(name=f"teacher-test-other-{_suffix()}", year=2026)
    )
    updated = await service.update_teacher(
        uuid.UUID(created.id),
        TeacherUpdateDTO(
            first_name="Jean",
            last_name="Martin",
            email=created.email,
            cohort_ids=[str(other_cohort.id)],
        ),
    )

    assert updated.cohort_names == [other_cohort.name]


async def test_delete_teacher_deactivates_and_deletes_keycloak_user(seeded_cohort):
    keycloak = _FakeKeycloakService()
    service = TeacherService(keycloak_service=keycloak, mail_service=_FakeMailService())

    created = await service.create_teacher(
        TeacherCreateDTO(
            first_name="Jean",
            last_name="Martin",
            email=f"jean.martin-{_suffix()}@test.local",
            cohort_ids=[str(seeded_cohort.id)],
        )
    )

    await service.delete_teacher(uuid.UUID(created.id))

    teacher_repo = TeacherRepository()
    teacher = await teacher_repo.get(uuid.UUID(created.id))
    assert teacher.is_active is False
    assert any(c[0] == "delete_user" for c in keycloak.calls)


async def test_list_students_for_teacher_scopes_to_assigned_cohorts(seeded_cohort):
    keycloak = _FakeKeycloakService()
    service = TeacherService(keycloak_service=keycloak, mail_service=_FakeMailService())
    teacher_keycloak_id = uuid.uuid4()

    created = await service.create_teacher(
        TeacherCreateDTO(
            first_name="Jean",
            last_name="Martin",
            email=f"jean.martin-{_suffix()}@test.local",
            cohort_ids=[str(seeded_cohort.id)],
        )
    )
    teacher_repo = TeacherRepository()
    await teacher_repo.update(
        uuid.UUID(created.id), {"keycloak_user_id": teacher_keycloak_id}
    )

    now = datetime.now(UTC).replace(tzinfo=None)
    other_cohort = await CohortRepository().add(
        Cohort(
            name=f"teacher-test-outside-{_suffix()}",
            year=2026,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=300),
        )
    )

    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()

    in_scope_student = await student_repo.add(
        Student(
            external_id=int(uuid.uuid4().int % 1_000_000),
            last_name="InScope",
            first_name="Student",
            email=f"inscope-{_suffix()}@test.local",
            login=f"inscope-{_suffix()}",
            keycloak_user_id=uuid.uuid4(),
        )
    )
    await enrollment_repo.add(
        Enrollment(student_id=in_scope_student.id, cohort_id=seeded_cohort.id)
    )

    outside_student = await student_repo.add(
        Student(
            external_id=int(uuid.uuid4().int % 1_000_000),
            last_name="Outside",
            first_name="Student",
            email=f"outside-{_suffix()}@test.local",
            login=f"outside-{_suffix()}",
            keycloak_user_id=uuid.uuid4(),
        )
    )
    await enrollment_repo.add(
        Enrollment(student_id=outside_student.id, cohort_id=other_cohort.id)
    )

    page = await service.list_students_for_teacher(teacher_keycloak_id)

    assert page.total_count == 1
    assert page.items[0].login == in_scope_student.login


async def test_list_students_for_teacher_without_cohorts_returns_empty_page():
    service = TeacherService()
    page = await service.list_students_for_teacher(uuid.uuid4())
    assert page.total_count == 0
    assert page.items == []


async def test_create_teacher_links_existing_keycloak_account(seeded_cohort):
    """Un admin (compte Keycloak déjà existant) devient aussi prof sans
    nouveau compte ni mot de passe ni mail (#58, précision utilisateur)."""
    existing_kc_id = str(uuid.uuid4())
    keycloak = _FakeKeycloakService(
        existing_users={
            "simon.admin": {
                "id": existing_kc_id,
                "username": "simon.admin",
                "email": "simon.admin@test.local",
                "firstName": "Simon",
                "lastName": "Admin",
            }
        }
    )
    mail = _FakeMailService()
    service = TeacherService(keycloak_service=keycloak, mail_service=mail)

    data = TeacherCreateDTO(
        first_name="Simon",
        last_name="Admin",
        email="simon.admin@test.local",
        cohort_ids=[str(seeded_cohort.id)],
        keycloak_login="simon.admin",
    )
    result = await service.create_teacher(data)

    assert result.login == "simon.admin"
    assert result.cohort_names == [seeded_cohort.name]

    teacher_repo = TeacherRepository()
    teacher = await teacher_repo.get(uuid.UUID(result.id))
    assert str(teacher.keycloak_user_id) == existing_kc_id

    # Pas de nouveau compte créé, pas de mot de passe, pas de mail.
    assert not any(c[0] == "create_user" for c in keycloak.calls)
    assert not any(c[0] == "set_user_password" for c in keycloak.calls)
    assert mail.sent == []
    group_calls = [c for c in keycloak.calls if c[0] == "add_user_to_group"]
    assert group_calls[0][1]["group_name"] == "prof"


async def test_create_teacher_with_unknown_keycloak_login_raises_404(seeded_cohort):
    service = TeacherService(
        keycloak_service=_FakeKeycloakService(), mail_service=_FakeMailService()
    )
    data = TeacherCreateDTO(
        first_name="Simon",
        last_name="Admin",
        email="simon.admin@test.local",
        cohort_ids=[str(seeded_cohort.id)],
        keycloak_login="does-not-exist",
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_teacher(data)
    assert exc_info.value.status_code == 404


async def test_create_teacher_rejects_already_linked_keycloak_account(seeded_cohort):
    existing_kc_id = uuid.uuid4()
    keycloak = _FakeKeycloakService(
        existing_users={
            "simon.admin": {
                "id": str(existing_kc_id),
                "username": "simon.admin",
                "email": "simon.admin@test.local",
                "firstName": "Simon",
                "lastName": "Admin",
            }
        }
    )
    service = TeacherService(keycloak_service=keycloak, mail_service=_FakeMailService())
    data = TeacherCreateDTO(
        first_name="Simon",
        last_name="Admin",
        email="simon.admin@test.local",
        cohort_ids=[str(seeded_cohort.id)],
        keycloak_login="simon.admin",
    )
    await service.create_teacher(data)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_teacher(data)
    assert exc_info.value.status_code == 409


async def test_lookup_keycloak_user_returns_profile():
    keycloak = _FakeKeycloakService(
        existing_users={
            "simon.admin": {
                "id": str(uuid.uuid4()),
                "username": "simon.admin",
                "email": "simon.admin@test.local",
                "firstName": "Simon",
                "lastName": "Admin",
            }
        }
    )
    service = TeacherService(keycloak_service=keycloak)
    result = await service.lookup_keycloak_user("simon.admin")
    assert result.login == "simon.admin"
    assert result.email == "simon.admin@test.local"
    assert result.first_name == "Simon"
    assert result.last_name == "Admin"


async def test_lookup_keycloak_user_unknown_login_raises_404():
    service = TeacherService(keycloak_service=_FakeKeycloakService())
    with pytest.raises(HTTPException) as exc_info:
        await service.lookup_keycloak_user("does-not-exist")
    assert exc_info.value.status_code == 404

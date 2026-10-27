"""Pagination du filtre cohort sur la recherche étudiants.

Avant correction, `StudentService.list_students` appliquait le filtre
`cohort` en Python *après* le LIMIT/OFFSET SQL, et `total_count` ne tenait
jamais compte du filtre : avec plus d'étudiants que `size` répartis sur
plusieurs cohorts, une page pouvait renvoyer moins d'items que `size` tout
en annonçant un `total_count` erroné (comptant tous les étudiants actifs,
pas seulement ceux de la cohort filtrée).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.models.enrollment import Enrollment
from labomatics.core.db.models.student import Student
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.enrollment import EnrollmentRepository
from labomatics.core.db.repository.student import StudentRepository
from labomatics.services.student_service import StudentService

MANAGE_USER = ["manage_user"]


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


async def _create_student_in_cohort(cohort_id, suffix: str) -> Student:
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    student = await student_repo.add(
        Student(
            external_id=int(uuid.uuid4().int % 1_000_000),
            last_name="Pagination",
            first_name=f"Test-{suffix}",
            email=f"pagination-{suffix}@test.local",
            login=f"pagination-{suffix}",
            keycloak_user_id=uuid.uuid4(),
        )
    )
    await enrollment_repo.add(Enrollment(student_id=student.id, cohort_id=cohort_id))
    return student


async def test_cohort_filter_total_count_matches_filtered_items():
    cohort_repo = CohortRepository()
    suffix = _suffix()
    now = datetime.now(UTC).replace(tzinfo=None)

    target_cohort = await cohort_repo.add(
        Cohort(
            name=f"pagination-target-{suffix}",
            year=2026,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=300),
        )
    )
    other_cohort = await cohort_repo.add(
        Cohort(
            name=f"pagination-other-{suffix}",
            year=2026,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=300),
        )
    )

    # Plus d'étudiants dans la cohort cible que la taille de page demandée,
    # plus des étudiants d'une autre cohort qui ne doivent jamais apparaître.
    for i in range(3):
        await _create_student_in_cohort(target_cohort.id, f"{suffix}-target-{i}")
    for i in range(3):
        await _create_student_in_cohort(other_cohort.id, f"{suffix}-other-{i}")

    service = StudentService()
    page = await service.list_students(page=1, size=2, cohort=target_cohort.name)

    assert page.total_count == 3
    assert page.total_pages == 2
    assert len(page.items) == 2
    assert all(item.cohort_name == target_cohort.name for item in page.items)


async def test_cohort_filter_unknown_name_returns_empty_page():
    service = StudentService()
    page = await service.list_students(page=1, size=20, cohort=f"unknown-{_suffix()}")

    assert page.total_count == 0
    assert page.items == []


async def test_cohort_ids_empty_list_returns_empty_page_not_everyone():
    service = StudentService()
    page = await service.list_students(page=1, size=20, cohort_ids=[])

    assert page.total_count == 0
    assert page.items == []

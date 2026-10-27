"""Tests unitaires — issue #74.

Un étudiant ne peut pas créer de lab sur un cluster hors de sa promo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.models.cohort_cluster import CohortCluster
from labomatics.core.db.models.enrollment import Enrollment
from labomatics.core.db.models.student import Student
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.cohort_cluster import CohortClusterRepository
from labomatics.core.db.repository.enrollment import EnrollmentRepository
from labomatics.core.db.repository.student import StudentRepository
from labomatics.services.lab_service import LabService


@pytest.fixture
async def student_in_cohort_with_one_allowed_cluster():
    """Étudiant actif dans une cohort n'ayant qu'un seul cluster autorisé."""
    suffix = uuid.uuid4().hex[:8]
    cohort_repo = CohortRepository()
    cluster_repo = ClusterRepository()
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    cohort_cluster_repo = CohortClusterRepository()

    cohort = await cohort_repo.add(Cohort(name=f"lab-test-{suffix}", year=2026))
    allowed_cluster = await cluster_repo.add(
        Cluster(
            name=f"lab-test-allowed-{suffix}",
            url="https://proxmox.invalid:8006",
            default_storage="local",
            sdn_zone="zone1",
        )
    )
    other_cluster = await cluster_repo.add(
        Cluster(
            name=f"lab-test-other-{suffix}",
            url="https://proxmox.invalid:8006",
            default_storage="local",
            sdn_zone="zone1",
        )
    )
    student = await student_repo.add(
        Student(
            external_id=int(uuid.uuid4().int % 1_000_000),
            last_name="Test",
            first_name="RBAC",
            email=f"rbac-lab-{suffix}@test.local",
            login=f"rbac-lab-{suffix}",
            keycloak_user_id=uuid.uuid4(),
        )
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    await enrollment_repo.add(
        Enrollment(
            student_id=student.id,
            cohort_id=cohort.id,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=300),
        )
    )
    await cohort_cluster_repo.add(
        CohortCluster(cohort_id=cohort.id, cluster_id=allowed_cluster.id)
    )

    # Pas de nettoyage manuel : transaction annulée en fin de test
    # (voir `conftest._db_transaction_rollback`).
    yield student, allowed_cluster, other_cluster


async def test_cluster_outside_cohort_is_forbidden(
    student_in_cohort_with_one_allowed_cluster,
):
    student, _allowed_cluster, other_cluster = (
        student_in_cohort_with_one_allowed_cluster
    )
    with pytest.raises(HTTPException) as exc_info:
        await LabService()._ensure_cluster_allowed_for_student(
            student, other_cluster.id
        )
    assert exc_info.value.status_code == 403


async def test_cluster_inside_cohort_is_allowed(
    student_in_cohort_with_one_allowed_cluster,
):
    student, allowed_cluster, _other_cluster = (
        student_in_cohort_with_one_allowed_cluster
    )
    # Ne doit lever aucune exception.
    await LabService()._ensure_cluster_allowed_for_student(student, allowed_cluster.id)

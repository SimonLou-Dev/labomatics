"""Verrou de retrait de cluster sur une cohort — issue #53.

Le retrait d'un cluster assigné à une cohort doit être bloqué (409) tant
qu'un étudiant de la cohort a un lab provisioning/actif sur ce cluster.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.models.cohort_cluster import CohortCluster
from labomatics.core.db.models.enrollment import Enrollment
from labomatics.core.db.models.lab_provisioning import LabProvisioning
from labomatics.core.db.models.student import Student
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.cohort_cluster import CohortClusterRepository
from labomatics.core.db.repository.enrollment import EnrollmentRepository
from labomatics.core.db.repository.lab_provisioning import LabProvisioningRepository
from labomatics.core.db.repository.student import StudentRepository

MANAGE_CLUSTER = ["manage_cluster"]


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _csrf_headers(resp) -> dict[str, str]:
    return {"x-csrf-token": resp.headers["x-csrf-token"]}


async def _seed_cohort_cluster_student(*, cohort_end_offset_days: int = 300):
    """Cohort (avec fenêtre de dates) + cluster assigné + étudiant inscrit.

    La durée est désormais portée par la Cohort, pas par l'Enrollment (#53) :
    `cohort_end_offset_days` négatif simule une cohort dont l'année scolaire
    est déjà terminée.
    """
    suffix = _suffix()
    cohort_repo = CohortRepository()
    cluster_repo = ClusterRepository()
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    cohort_cluster_repo = CohortClusterRepository()

    now = datetime.now(UTC).replace(tzinfo=None)
    cohort = await cohort_repo.add(
        Cohort(
            name=f"lock-test-{suffix}",
            year=2026,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=cohort_end_offset_days),
        )
    )
    cluster = await cluster_repo.add(
        Cluster(
            name=f"lock-test-cluster-{suffix}",
            url="https://proxmox.invalid:8006",
            default_storage="local",
            sdn_zone="zone1",
        )
    )
    await cohort_cluster_repo.add(
        CohortCluster(cohort_id=cohort.id, cluster_id=cluster.id)
    )
    student = await student_repo.add(
        Student(
            external_id=int(uuid.uuid4().int % 1_000_000),
            last_name="Lock",
            first_name="Test",
            email=f"lock-test-{suffix}@test.local",
            login=f"lock-test-{suffix}",
            keycloak_user_id=uuid.uuid4(),
        )
    )
    await enrollment_repo.add(Enrollment(student_id=student.id, cohort_id=cohort.id))
    return cohort, cluster, student


async def _seed_lab_provisioning(student: Student, cluster: Cluster, status: str):
    repo = LabProvisioningRepository()
    return await repo.add(
        LabProvisioning(
            owner_keycloak_id=student.keycloak_user_id,
            owner_role="student",
            student_id=student.id,
            cluster_id=cluster.id,
            status=status,
            access_origin="self_service",
        )
    )


async def test_remove_cluster_blocked_when_active_lab_exists(client, override_user):
    cohort, cluster, student = await _seed_cohort_cluster_student()
    await _seed_lab_provisioning(student, cluster, status="active")

    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.delete(
        f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}",
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 409


async def test_remove_cluster_allowed_when_no_active_lab(client, override_user):
    cohort, cluster, _student = await _seed_cohort_cluster_student()

    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.delete(
        f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}",
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 200


async def test_remove_cluster_allowed_when_cohort_expired(client, override_user):
    cohort, cluster, student = await _seed_cohort_cluster_student(
        cohort_end_offset_days=-1
    )
    await _seed_lab_provisioning(student, cluster, status="active")

    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.delete(
        f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}",
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 200


async def test_remove_cluster_allowed_when_lab_status_error(client, override_user):
    cohort, cluster, student = await _seed_cohort_cluster_student()
    await _seed_lab_provisioning(student, cluster, status="error")

    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.delete(
        f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}",
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 200


async def test_cluster_ref_dto_has_active_lab_flag_reflects_lock_state(
    client, override_user
):
    cohort, cluster, student = await _seed_cohort_cluster_student()
    await _seed_lab_provisioning(student, cluster, status="provisioning")

    override_user(MANAGE_CLUSTER)
    resp = await client.get("/v1/cohorts", params={"size": 100})
    assert resp.status_code == 200
    item = next(c for c in resp.json()["items"] if c["id"] == str(cohort.id))
    cluster_ref = next(c for c in item["clusters"] if c["id"] == str(cluster.id))
    assert cluster_ref["has_active_lab"] is True

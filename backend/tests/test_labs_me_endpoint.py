"""GET /labs/me et POST /labs pour un owner teacher/admin — issue #58.

`GET /labs/me` ne gérait auparavant qu'un `Student` ; un teacher/admin
recevait toujours `None` même avec un lab actif. `POST /labs` sans
`cluster_id` pour un owner non-student échouait silencieusement dans le
job Celery — désormais rejeté en 422 avant l'enqueue.
"""

from __future__ import annotations

import uuid

from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.models.lab_provisioning import LabProvisioning
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.lab_provisioning import LabProvisioningRepository

DEFAULT_SUBJECT = "00000000-0000-0000-0000-000000000000"


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


async def test_get_my_lab_returns_none_for_teacher_without_lab(client, override_user):
    override_user(["teacher"])
    resp = await client.get("/v1/labs/me")
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_my_lab_returns_owner_data_for_teacher_with_lab(
    client, override_user
):
    cluster_repo = ClusterRepository()
    cluster = await cluster_repo.add(
        Cluster(
            name=f"labs-me-test-{_suffix()}",
            url="https://proxmox.invalid:8006",
            default_storage="local",
            sdn_zone="zone1",
        )
    )
    lab_prov_repo = LabProvisioningRepository()
    await lab_prov_repo.add(
        LabProvisioning(
            owner_keycloak_id=uuid.UUID(DEFAULT_SUBJECT),
            owner_role="teacher",
            student_id=None,
            cluster_id=cluster.id,
            status="active",
            access_origin="self_service",
        )
    )

    override_user(["teacher"], subject=DEFAULT_SUBJECT)
    resp = await client.get("/v1/labs/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["owner"]["role"] == "teacher"
    assert body["owner"]["cohort_name"] is None


async def test_create_lab_without_cluster_id_rejected_for_teacher(
    client, override_user
):
    override_user(["teacher"])
    first = await client.get("/v1/labs/me")
    resp = await client.post(
        "/v1/labs", headers={"x-csrf-token": first.headers["x-csrf-token"]}
    )
    assert resp.status_code == 422

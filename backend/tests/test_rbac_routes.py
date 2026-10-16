"""Tests d'intégration RBAC — issue #74.

Pour chaque route durcie : un rôle insuffisant doit recevoir 403, et le rôle
requis doit dépasser la vérification de rôle (200, ou un échec métier normal
quand aucune ressource réelle n'est disponible dans l'environnement de test,
mais jamais un 403).
"""

from __future__ import annotations

import uuid

import pytest

from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.models.ip_range import IpRange
from labomatics.core.db.models.vxlan_range import VxlanRange
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.ip_range import IpRangeRepository
from labomatics.core.db.repository.vxlan_range import VxlanRangeRepository

STUDENT = ["student"]


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _csrf_headers(resp) -> dict[str, str]:
    """En-tête CSRF à renvoyer pour le prochain appel mutateur du même client.

    `CSRFMiddleware` pose un cookie `csrf_token` dès la première réponse ; tout
    appel POST/PUT/PATCH/DELETE suivant avec ce cookie mais sans le header
    associé est rejeté (403), indépendamment du rôle — rien à voir avec le RBAC.
    """
    return {"x-csrf-token": resp.headers["x-csrf-token"]}


@pytest.fixture
async def seeded_cohort_cluster():
    """Cohort + cluster réels (pour cohorts.py).

    Pas de nettoyage manuel : chaque test tourne dans une transaction annulée
    à la fin (voir `conftest._db_transaction_rollback`), rien n'est jamais
    réellement écrit en base.
    """
    cohort_repo = CohortRepository()
    cluster_repo = ClusterRepository()
    suffix = _suffix()

    cohort = await cohort_repo.add(Cohort(name=f"rbac-test-{suffix}", year=2026))
    cluster = await cluster_repo.add(
        Cluster(
            name=f"rbac-test-cluster-{suffix}",
            url="https://proxmox.invalid:8006",
            default_storage="local",
            sdn_zone="zone1",
        )
    )
    yield cohort, cluster


@pytest.fixture
async def seeded_ip_range():
    repo = IpRangeRepository()
    suffix = _suffix()
    ip_range = await repo.add(
        IpRange(
            name=f"rbac-test-{suffix}",
            network="203.0.113.0/24",
            gateway="203.0.113.1",
        )
    )
    yield ip_range


@pytest.fixture
async def seeded_vxlan_range():
    repo = VxlanRangeRepository()
    suffix = _suffix()
    vxlan_range = await repo.add(
        VxlanRange(
            name=f"rbac-test-{suffix}",
            vni_min=100,
            vni_max=200,
            base_network="10.200.0.0/16",
        )
    )
    yield vxlan_range


# ---------------------------------------------------------------------------
# cohorts.py — RequireManageCluster sur les 4 endpoints
# ---------------------------------------------------------------------------


async def test_list_cohorts_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.get("/v1/cohorts")
    assert resp.status_code == 403


async def test_list_cohorts_ok_for_manage_cluster(client, override_user):
    override_user(["manage_cluster"])
    resp = await client.get("/v1/cohorts")
    assert resp.status_code == 200


async def test_assign_cluster_to_cohort_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.post(f"/v1/cohorts/{uuid.uuid4()}/clusters/{uuid.uuid4()}")
    assert resp.status_code == 403


async def test_assign_cluster_to_cohort_ok_for_manage_cluster(
    client, override_user, seeded_cohort_cluster
):
    cohort, cluster = seeded_cohort_cluster
    override_user(["manage_cluster"])
    resp = await client.post(f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}")
    assert resp.status_code == 200
    assert any(c["id"] == str(cluster.id) for c in resp.json()["clusters"])


async def test_set_default_cluster_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.patch(
        f"/v1/cohorts/{uuid.uuid4()}/clusters/{uuid.uuid4()}/set-default"
    )
    assert resp.status_code == 403


async def test_set_default_cluster_ok_for_manage_cluster(
    client, override_user, seeded_cohort_cluster
):
    cohort, cluster = seeded_cohort_cluster
    override_user(["manage_cluster"])
    assign_resp = await client.post(f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}")

    resp = await client.patch(
        f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}/set-default",
        headers=_csrf_headers(assign_resp),
    )
    assert resp.status_code == 200
    clusters = resp.json()["clusters"]
    assert next(c for c in clusters if c["id"] == str(cluster.id))["is_default"] is True


async def test_remove_cluster_from_cohort_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.delete(f"/v1/cohorts/{uuid.uuid4()}/clusters/{uuid.uuid4()}")
    assert resp.status_code == 403


async def test_remove_cluster_from_cohort_ok_for_manage_cluster(
    client, override_user, seeded_cohort_cluster
):
    cohort, cluster = seeded_cohort_cluster
    override_user(["manage_cluster"])
    assign_resp = await client.post(f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}")

    resp = await client.delete(
        f"/v1/cohorts/{cohort.id}/clusters/{cluster.id}",
        headers=_csrf_headers(assign_resp),
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# students.py — RequireManageUser sur GET /students
# ---------------------------------------------------------------------------


async def test_list_students_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.get("/v1/students")
    assert resp.status_code == 403


async def test_list_students_ok_for_manage_user(client, override_user):
    override_user(["manage_user"])
    resp = await client.get("/v1/students")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# ip_ranges.py / vxlan_ranges.py — RequireManageUser sur /allocations
# ---------------------------------------------------------------------------


async def test_ip_range_allocations_forbidden_for_student(
    client, override_user, seeded_ip_range
):
    override_user(STUDENT)
    resp = await client.get(f"/v1/ip-ranges/{seeded_ip_range.id}/allocations")
    assert resp.status_code == 403


async def test_ip_range_allocations_ok_for_manage_user(
    client, override_user, seeded_ip_range
):
    override_user(["manage_user"])
    resp = await client.get(f"/v1/ip-ranges/{seeded_ip_range.id}/allocations")
    assert resp.status_code == 200


async def test_vxlan_range_allocations_forbidden_for_student(
    client, override_user, seeded_vxlan_range
):
    override_user(STUDENT)
    resp = await client.get(f"/v1/vxlan-ranges/{seeded_vxlan_range.id}/allocations")
    assert resp.status_code == 403


async def test_vxlan_range_allocations_ok_for_manage_user(
    client, override_user, seeded_vxlan_range
):
    override_user(["manage_user"])
    resp = await client.get(f"/v1/vxlan-ranges/{seeded_vxlan_range.id}/allocations")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# clusters.py — RequireManageCluster sur /test-connection
# ---------------------------------------------------------------------------


async def test_cluster_test_connection_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.post(f"/v1/clusters/{uuid.uuid4()}/test-connection")
    assert resp.status_code == 403


async def test_cluster_test_connection_passes_rbac_for_manage_cluster(
    client, override_user
):
    # Aucun cluster Proxmox réel dans l'environnement de test : on vérifie que
    # la vérification de rôle est bien dépassée (plus jamais 403), l'échec
    # ensuite (404 cluster introuvable) relève du domaine métier, pas du RBAC.
    override_user(["manage_cluster"])
    resp = await client.post(f"/v1/clusters/{uuid.uuid4()}/test-connection")
    assert resp.status_code != 403
    assert resp.status_code == 404

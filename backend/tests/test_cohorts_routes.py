"""Tests sur les routes cohorts.py — issue #53.

Typage UUID (422 sur ID invalide au lieu d'un 500), mise à jour des dates et
format de l'année scolaire.
"""

from __future__ import annotations

import uuid

import pytest

from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.repository.cohort import CohortRepository

MANAGE_CLUSTER = ["manage_cluster"]


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _csrf_headers(resp) -> dict[str, str]:
    return {"x-csrf-token": resp.headers["x-csrf-token"]}


@pytest.fixture
async def seeded_cohort():
    repo = CohortRepository()
    cohort = await repo.add(Cohort(name=f"cohort-routes-{_suffix()}", year=2026))
    yield cohort


async def test_assign_cluster_to_cohort_invalid_uuid_returns_422(client, override_user):
    override_user(MANAGE_CLUSTER)
    resp = await client.post("/v1/cohorts/not-a-uuid/clusters/not-a-uuid")
    assert resp.status_code == 422


async def test_remove_cluster_from_cohort_invalid_uuid_returns_422(
    client, override_user
):
    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.delete(
        "/v1/cohorts/not-a-uuid/clusters/not-a-uuid",
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 422


async def test_set_default_cluster_invalid_uuid_returns_422(client, override_user):
    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.patch(
        "/v1/cohorts/not-a-uuid/clusters/not-a-uuid/set-default",
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 422


async def test_update_cohort_dates_persists(client, override_user, seeded_cohort):
    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.patch(
        f"/v1/cohorts/{seeded_cohort.id}",
        json={"start_date": "2026-09-01T00:00:00", "end_date": "2027-08-31T00:00:00"},
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["start_date"].startswith("2026-09-01")
    assert body["end_date"].startswith("2027-08-31")


async def test_update_cohort_unknown_id_returns_404(client, override_user):
    override_user(MANAGE_CLUSTER)
    first = await client.get("/v1/cohorts")
    resp = await client.patch(
        f"/v1/cohorts/{uuid.uuid4()}",
        json={"start_date": "2026-09-01T00:00:00"},
        headers=_csrf_headers(first),
    )
    assert resp.status_code == 404


async def test_cohort_dto_exposes_school_year_format(client, override_user):
    override_user(MANAGE_CLUSTER)
    repo = CohortRepository()
    cohort = await repo.add(Cohort(name=f"cohort-school-year-{_suffix()}", year=2025))

    resp = await client.get("/v1/cohorts", params={"size": 100})
    assert resp.status_code == 200
    item = next(c for c in resp.json()["items"] if c["id"] == str(cohort.id))
    assert item["school_year"] == "2025-2026"

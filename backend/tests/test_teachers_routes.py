"""Tests RBAC + comportement sur les routes teachers.py — issue #58.

Pour les routes mutatives, on vérifie le RBAC via un échec métier normal
(404 sur un ID/cohort inconnu) plutôt que d'appeler le vrai Keycloak —
même convention que `test_cluster_test_connection_passes_rbac_for_manage_cluster`
dans `test_rbac_routes.py`.
"""

from __future__ import annotations

import uuid

STUDENT = ["student"]
MANAGE_USER = ["manage_user"]


def _csrf_headers(resp) -> dict[str, str]:
    return {"x-csrf-token": resp.headers["x-csrf-token"]}


async def test_list_teachers_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.get("/v1/teachers")
    assert resp.status_code == 403


async def test_list_teachers_ok_for_manage_user(client, override_user):
    override_user(MANAGE_USER)
    resp = await client.get("/v1/teachers")
    assert resp.status_code == 200


async def test_create_teacher_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.post(
        "/v1/teachers",
        json={
            "first_name": "Jean",
            "last_name": "Dupont",
            "email": "jean.dupont@test.local",
            "cohort_ids": [],
        },
    )
    assert resp.status_code == 403


async def test_create_teacher_passes_rbac_for_manage_user(client, override_user):
    override_user(MANAGE_USER)
    first = await client.get("/v1/teachers")
    resp = await client.post(
        "/v1/teachers",
        json={
            "first_name": "Jean",
            "last_name": "Dupont",
            "email": f"jean.dupont-{uuid.uuid4().hex[:8]}@test.local",
            "cohort_ids": [str(uuid.uuid4())],
        },
        headers=_csrf_headers(first),
    )
    assert resp.status_code != 403
    assert resp.status_code == 404


async def test_update_teacher_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.patch(
        f"/v1/teachers/{uuid.uuid4()}",
        json={
            "first_name": "Jean",
            "last_name": "Dupont",
            "email": "jean.dupont@test.local",
            "cohort_ids": [],
        },
    )
    assert resp.status_code == 403


async def test_update_teacher_passes_rbac_for_manage_user(client, override_user):
    override_user(MANAGE_USER)
    first = await client.get("/v1/teachers")
    resp = await client.patch(
        f"/v1/teachers/{uuid.uuid4()}",
        json={
            "first_name": "Jean",
            "last_name": "Dupont",
            "email": "jean.dupont@test.local",
            "cohort_ids": [],
        },
        headers=_csrf_headers(first),
    )
    assert resp.status_code != 403
    assert resp.status_code == 404


async def test_delete_teacher_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.delete(f"/v1/teachers/{uuid.uuid4()}")
    assert resp.status_code == 403


async def test_delete_teacher_passes_rbac_for_manage_user(client, override_user):
    override_user(MANAGE_USER)
    first = await client.get("/v1/teachers")
    resp = await client.delete(
        f"/v1/teachers/{uuid.uuid4()}", headers=_csrf_headers(first)
    )
    assert resp.status_code != 403
    assert resp.status_code == 404


async def test_list_my_students_forbidden_for_student(client, override_user):
    override_user(STUDENT)
    resp = await client.get("/v1/teachers/me/students")
    assert resp.status_code == 403


async def test_list_my_students_ok_for_teacher(client, override_user):
    override_user(["teacher"])
    resp = await client.get("/v1/teachers/me/students")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_list_my_students_ok_for_admin_without_explicit_teacher_role(
    client, override_user
):
    """Un admin est aussi un prof (précision utilisateur, #58) : pas de 403."""
    override_user(["admin"])
    resp = await client.get("/v1/teachers/me/students")
    assert resp.status_code == 200

"""Tests unitaires — issue #61 : purge des audit logs de plus d'un mois."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from labomatics.core.db.models.audit_log import AuditLog
from labomatics.core.db.repository.audit_log import AuditLogRepository
from labomatics.core.db.session import async_session_local


async def test_delete_older_than_removes_only_old_entries():
    repo = AuditLogRepository()
    actor = str(uuid.uuid4())

    old_entry = await repo.add(
        AuditLog(
            actor_keycloak_id=actor,
            actor_role="admin",
            action="test_old",
            resource_type="test",
        )
    )
    recent_entry = await repo.add(
        AuditLog(
            actor_keycloak_id=actor,
            actor_role="admin",
            action="test_recent",
            resource_type="test",
        )
    )

    # `created_at` est fixé par défaut à "maintenant" à l'insertion : on le
    # recule artificiellement en base pour simuler un log d'il y a 60 jours.
    old_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60)
    async with async_session_local() as session:
        await session.execute(
            update(AuditLog)
            .where(AuditLog.id == old_entry.id)
            .values(created_at=old_date)
        )
        await session.commit()

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
    deleted = await repo.delete_older_than(cutoff)

    assert deleted >= 1
    assert await repo.get(old_entry.id) is None
    assert await repo.get(recent_entry.id) is not None

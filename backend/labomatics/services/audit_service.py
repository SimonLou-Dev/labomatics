"""Service pour l'enregistrement des événements d'audit.

Logging des actions sensibles en base de données (best-effort).
"""

from __future__ import annotations

import logging
from uuid import UUID

from labomatics.constants.enums import EventType
from labomatics.core.db.models.audit_log import AuditLog
from labomatics.core.db.repository.audit_log import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Service pour l'enregistrement des événements d'audit."""

    def __init__(self, repo: AuditLogRepository | None = None) -> None:
        """Initialise le service avec un repository optionnel.

        Args:
            repo: AuditLogRepository (créé si None).
        """
        self.repo = repo or AuditLogRepository()

    async def log(
        self,
        *,
        actor_keycloak_id: str | UUID,
        actor_role: str,
        action: EventType,
        resource_type: str,
        resource_id: str | UUID | None = None,
        details: dict | None = None,
    ) -> None:
        """Enregistre un événement d'audit (best-effort, ne lève pas).

        Args:
            actor_keycloak_id: UUID Keycloak du principal (str ou UUID).
            actor_role: Rôle de l'acteur (student/teacher/admin/...).
            action: Type d'action (EventType enum).
            resource_type: Type de ressource affectée (lab/vm/...).
            resource_id: ID optionnel de la ressource.
            details: Détails JSON optionnels de l'action.
        """
        try:
            audit_log = AuditLog(
                actor_keycloak_id=str(actor_keycloak_id),
                actor_role=actor_role,
                action=str(action),  # StrEnum → string
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                details=details,
            )
            await self.repo.add(audit_log)
        except Exception as e:
            # best-effort : log en console mais ne lève pas
            logger.warning(f"Failed to log audit event: {e}", exc_info=True)

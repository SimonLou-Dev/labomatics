"""Enums categorielles du domaine labomatics.

Tout ce qui est categoriel est un `StrEnum` (serialisable directement en DTO).
Les valeurs sont les chaines stockees en base / exposees a l'API.
"""

from __future__ import annotations

from enum import StrEnum


class NotifType(StrEnum):
    """Type d'une notification temps reel (toast front)."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class OwnerRole(StrEnum):
    """Rôle du propriétaire d'un lab."""

    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class EventType(StrEnum):
    """Type d'événement d'audit pour la création de lab."""

    LAB_REQUESTED = "lab_requested"
    WAN_IP_ALLOCATED = "wan_ip_allocated"
    NETWORK_ALLOCATED = "network_allocated"
    ROUTER_CREATED = "router_created"
    LAB_CREATED = "lab_created"
    LAB_CREATION_FAILED = "lab_creation_failed"

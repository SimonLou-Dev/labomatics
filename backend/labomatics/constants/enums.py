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

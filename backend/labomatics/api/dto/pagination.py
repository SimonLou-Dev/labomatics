"""DTO de pagination."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedDTO(BaseModel, Generic[T]):
    """DTO de pagination générique."""

    items: Sequence[T]
    page: int
    per_page: int
    total: int
    total_pages: int

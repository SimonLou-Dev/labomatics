from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Mixin fournissant created_at et updated_at sur toutes les tables."""

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
        onupdate=lambda: datetime.utcnow().replace(tzinfo=None),
        server_default=func.now(),
    )

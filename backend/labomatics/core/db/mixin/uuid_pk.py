from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPkMixin:
    """Mixin fournissant une clé primaire UUID auto-générée sur toutes les tables."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

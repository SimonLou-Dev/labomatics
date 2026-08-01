from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column


class UUIDPkMixin:
    """Mixin fournissant une clé primaire UUID auto-générée sur toutes les tables."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

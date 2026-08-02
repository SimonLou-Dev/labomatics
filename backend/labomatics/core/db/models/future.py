from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin

# === TP / EXERCISE (v0.7) ===


class Exercise(Base, UUIDPkMixin, TimestampMixin):
    """TP/Exercice pratique (futur v0.7)."""

    __tablename__ = "exercise"

    name: Mapped[str]
    owner_keycloak_id: Mapped[UUID] = mapped_column()
    is_active: Mapped[bool] = mapped_column(
        default=True,
    )

    # Relationships
    versions: Mapped[list["ExerciseVersion"]] = relationship(
        back_populates="exercise",
    )


class ExerciseVersion(Base, UUIDPkMixin, TimestampMixin):
    """Version d'un exercice (versionnage, modif = nouvelle version)."""

    __tablename__ = "exercise_version"

    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise.id", ondelete="RESTRICT"),
    )
    version_number: Mapped[int]
    definition: Mapped[dict] = mapped_column(
        JSON,
    )
    duration_hours: Mapped[int | None] = None
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )

    # Relationships
    exercise: Mapped["Exercise"] = relationship(
        back_populates="versions",
    )
    cohorts: Mapped[list["ExerciseVersionCohort"]] = relationship(
        back_populates="exercise_version",
    )
    campaigns: Mapped[list["ExerciseDeploymentCampaign"]] = relationship(
        back_populates="exercise_version",
    )

    __table_args__ = (UniqueConstraint("exercise_id", "version_number"),)


class ExerciseVersionCohort(Base, UUIDPkMixin, TimestampMixin):
    """Assignation exercise_version → cohorts."""

    __tablename__ = "exercise_version_cohort"

    exercise_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_version.id", ondelete="RESTRICT"),
    )
    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
    )

    # Relationships
    exercise_version: Mapped["ExerciseVersion"] = relationship(
        back_populates="cohorts",
    )
    cohort: Mapped["Cohort"] = relationship()  # type: ignore

    __table_args__ = (UniqueConstraint("exercise_version_id", "cohort_id"),)


class ExerciseDeploymentCampaign(Base, UUIDPkMixin, TimestampMixin):
    """Campagne de déploiement TP (individuel ou masse)."""

    __tablename__ = "exercise_deployment_campaign"

    exercise_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_version.id", ondelete="RESTRICT"),
    )
    mode: Mapped[str] = mapped_column()
    triggered_by_keycloak_id: Mapped[UUID]
    triggered_by_role: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    requested_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )
    expected_end_at: Mapped[datetime | None] = None
    completed_at: Mapped[datetime | None] = None

    # Relationships
    exercise_version: Mapped["ExerciseVersion"] = relationship(
        back_populates="campaigns",
    )
    instances: Mapped[list["ExerciseDeploymentInstance"]] = relationship(
        back_populates="campaign",
    )


class ExerciseDeploymentInstance(Base, UUIDPkMixin, TimestampMixin):
    """Instance de déploiement (une ligne par VM, y compris mode individuel)."""

    __tablename__ = "exercise_deployment_instance"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_deployment_campaign.id", ondelete="RESTRICT"),
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
    )
    proxmox_vm_id: Mapped[int | None] = None
    proxmox_tag: Mapped[str] = mapped_column(
        default="exercise",
    )
    status: Mapped[str] = mapped_column()
    provisioned_at: Mapped[datetime | None] = None
    last_stopped_at: Mapped[datetime | None] = None
    deleted_at: Mapped[datetime | None] = None

    # Relationships
    campaign: Mapped["ExerciseDeploymentCampaign"] = relationship(
        back_populates="instances",
    )
    student: Mapped["Student"] = relationship()  # type: ignore
    cluster: Mapped["Cluster"] = relationship()  # type: ignore


# === QUOTAS (v0.8) ===


class QuotaDefault(Base, UUIDPkMixin, TimestampMixin):
    """Quota par défaut pour une promo."""

    __tablename__ = "quota_default"

    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
        unique=True,
    )
    cpu_limit: Mapped[int | None] = None
    ram_limit_mb: Mapped[int | None] = None
    disk_limit_gb: Mapped[int | None] = None

    # Relationships
    cohort: Mapped["Cohort"] = relationship()  # type: ignore


class QuotaOverride(Base, UUIDPkMixin, TimestampMixin):
    """Override de quota pour un étudiant (figé une fois posé)."""

    __tablename__ = "quota_override"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
        unique=True,
    )
    cpu_limit: Mapped[int | None] = None
    ram_limit_mb: Mapped[int | None] = None
    disk_limit_gb: Mapped[int | None] = None
    locked_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )

    # Relationships
    student: Mapped["Student"] = relationship()  # type: ignore


class QuotaMeasurement(Base, UUIDPkMixin):
    """Mesure périodique de quota (résultat agrégation, exclut exercices)."""

    __tablename__ = "quota_measurement"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    measured_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )
    cpu_used: Mapped[int]
    ram_used_mb: Mapped[int]
    disk_used_gb: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )

    # Relationships
    student: Mapped["Student"] = relationship()  # type: ignore

    __table_args__ = (
        Index("idx_quota_measurement_student_date", "student_id", "measured_at"),
    )


# === DNS (v0.9) ===


class DnsRecord(Base, UUIDPkMixin, TimestampMixin):
    """Enregistrement DNS pour un étudiant (schéma flexible pour v0.9)."""

    __tablename__ = "dns_record"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    cluster_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
        nullable=True,
    )
    subdomain: Mapped[str] = mapped_column()
    target: Mapped[str] = mapped_column()

    # Relationships
    student: Mapped["Student"] = relationship()  # type: ignore
    cluster: Mapped[Optional["Cluster"]] = relationship()  # type: ignore

    __table_args__ = (UniqueConstraint("subdomain"),)


# Import forward references
from labomatics.core.db.models.cluster import Cluster  # noqa: E402
from labomatics.core.db.models.cohort import Cohort  # noqa: E402
from labomatics.core.db.models.student import Student  # noqa: E402

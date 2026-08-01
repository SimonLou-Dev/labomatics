"""Repositories pour l'accès aux données."""

from labomatics.core.db.repository.audit_log import AuditLogRepository
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cluster_credential import (
    ClusterCredentialRepository,
)
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.cohort_cluster import (
    CohortClusterRepository,
)
from labomatics.core.db.repository.enrollment import EnrollmentRepository
from labomatics.core.db.repository.ip_allocation import IpAllocationRepository
from labomatics.core.db.repository.ip_range import IpRangeRepository
from labomatics.core.db.repository.ip_range_cluster import (
    IpRangeClusterRepository,
)
from labomatics.core.db.repository.lab_provisioning import (
    LabProvisioningRepository,
)
from labomatics.core.db.repository.student import StudentRepository
from labomatics.core.db.repository.student_cluster_extra import (
    StudentClusterExtraRepository,
)
from labomatics.core.db.repository.teacher_cohort import TeacherCohortRepository
from labomatics.core.db.repository.vxlan_allocation import (
    VxlanAllocationRepository,
)
from labomatics.core.db.repository.vxlan_range import VxlanRangeRepository
from labomatics.core.db.repository.vxlan_range_cluster import (
    VxlanRangeClusterRepository,
)

__all__ = [
    "AuditLogRepository",
    "ClusterCredentialRepository",
    "ClusterRepository",
    "CohortClusterRepository",
    "CohortRepository",
    "EnrollmentRepository",
    "IpAllocationRepository",
    "IpRangeClusterRepository",
    "IpRangeRepository",
    "LabProvisioningRepository",
    "StudentClusterExtraRepository",
    "StudentRepository",
    "TeacherCohortRepository",
    "VxlanAllocationRepository",
    "VxlanRangeClusterRepository",
    "VxlanRangeRepository",
]

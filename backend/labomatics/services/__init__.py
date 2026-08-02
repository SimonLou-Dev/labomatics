"""Services package avec dependency injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from labomatics.services.auth_service import AuthService
from labomatics.services.cluster_config_service import ClusterConfigService
from labomatics.services.cluster_service import ClusterService
from labomatics.services.ip_range_service import IpRangeService
from labomatics.services.mail_service import MailService
from labomatics.services.student_import_service import StudentImportService
from labomatics.services.student_service import StudentService
from labomatics.services.vxlan_range_service import VxlanRangeService

__all__ = [
    "AuthService",
    "AuthServiceDep",
    "ClusterConfigService",
    "ClusterConfigServiceDep",
    "ClusterService",
    "ClusterServiceDep",
    "IpRangeService",
    "IpRangeServiceDep",
    "MailService",
    "MailServiceDep",
    "StudentImportService",
    "StudentImportServiceDep",
    "StudentService",
    "StudentServiceDep",
    "VxlanRangeService",
    "VxlanRangeServiceDep",
]


def get_auth_service() -> AuthService:
    """Factory pour AuthService."""
    return AuthService()


def get_mail_service() -> MailService:
    """Factory pour MailService."""
    return MailService()


def get_student_service() -> StudentService:
    """Factory pour StudentService."""
    return StudentService()


def get_student_import_service() -> StudentImportService:
    """Factory pour StudentImportService."""
    return StudentImportService()


def get_cluster_service() -> ClusterService:
    """Factory pour ClusterService."""
    return ClusterService()


def get_ip_range_service() -> IpRangeService:
    """Factory pour IpRangeService."""
    return IpRangeService()


def get_vxlan_range_service() -> VxlanRangeService:
    """Factory pour VxlanRangeService."""
    return VxlanRangeService()


def get_cluster_config_service() -> ClusterConfigService:
    """Factory pour ClusterConfigService."""
    return ClusterConfigService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
MailServiceDep = Annotated[MailService, Depends(get_mail_service)]
StudentServiceDep = Annotated[StudentService, Depends(get_student_service)]
StudentImportServiceDep = Annotated[
    StudentImportService, Depends(get_student_import_service)
]
ClusterServiceDep = Annotated[ClusterService, Depends(get_cluster_service)]
IpRangeServiceDep = Annotated[IpRangeService, Depends(get_ip_range_service)]
VxlanRangeServiceDep = Annotated[VxlanRangeService, Depends(get_vxlan_range_service)]
ClusterConfigServiceDep = Annotated[
    ClusterConfigService, Depends(get_cluster_config_service)
]

"""Services package avec dependency injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from labomatics.services.audit_service import AuditService
from labomatics.services.auth_service import AuthService
from labomatics.services.cluster_config_service import ClusterConfigService
from labomatics.services.cluster_service import ClusterService
from labomatics.services.ip_range_service import IpRangeService
from labomatics.services.keycloak_service import KeycloakService
from labomatics.services.lab_service import LabService
from labomatics.services.mail_service import MailService
from labomatics.services.network_range_service import NetworkRangeService
from labomatics.services.proxmox_service import ProxmoxService
from labomatics.services.student_import_service import StudentImportService
from labomatics.services.student_service import StudentService
from labomatics.services.vxlan_range_service import VxlanRangeService

__all__ = [
    "AuditService",
    "AuditServiceDep",
    "AuthService",
    "AuthServiceDep",
    "ClusterConfigService",
    "ClusterConfigServiceDep",
    "ClusterService",
    "ClusterServiceDep",
    "IpRangeService",
    "IpRangeServiceDep",
    "KeycloakService",
    "KeycloakServiceDep",
    "LabService",
    "LabServiceDep",
    "MailService",
    "MailServiceDep",
    "NetworkRangeService",
    "NetworkRangeServiceDep",
    "ProxmoxService",
    "ProxmoxServiceDep",
    "StudentImportService",
    "StudentImportServiceDep",
    "StudentService",
    "StudentServiceDep",
    "VxlanRangeService",
    "VxlanRangeServiceDep",
]


def get_audit_service() -> AuditService:
    """Factory pour AuditService."""
    return AuditService()


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


def get_network_range_service() -> NetworkRangeService:
    """Factory pour NetworkRangeService."""
    return NetworkRangeService()


def get_vxlan_range_service() -> VxlanRangeService:
    """Factory pour VxlanRangeService."""
    return VxlanRangeService()


def get_cluster_config_service() -> ClusterConfigService:
    """Factory pour ClusterConfigService."""
    return ClusterConfigService()


def get_keycloak_service() -> KeycloakService:
    """Factory pour KeycloakService."""
    return KeycloakService()


def get_lab_service() -> LabService:
    """Factory pour LabService."""
    return LabService()


def get_proxmox_service() -> ProxmoxService:
    """Factory pour ProxmoxService."""
    return ProxmoxService()


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
MailServiceDep = Annotated[MailService, Depends(get_mail_service)]
StudentServiceDep = Annotated[StudentService, Depends(get_student_service)]
StudentImportServiceDep = Annotated[
    StudentImportService, Depends(get_student_import_service)
]
ClusterServiceDep = Annotated[ClusterService, Depends(get_cluster_service)]
IpRangeServiceDep = Annotated[IpRangeService, Depends(get_ip_range_service)]
NetworkRangeServiceDep = Annotated[
    NetworkRangeService, Depends(get_network_range_service)
]
VxlanRangeServiceDep = Annotated[VxlanRangeService, Depends(get_vxlan_range_service)]
ClusterConfigServiceDep = Annotated[
    ClusterConfigService, Depends(get_cluster_config_service)
]
KeycloakServiceDep = Annotated[KeycloakService, Depends(get_keycloak_service)]
LabServiceDep = Annotated[LabService, Depends(get_lab_service)]
ProxmoxServiceDep = Annotated[ProxmoxService, Depends(get_proxmox_service)]

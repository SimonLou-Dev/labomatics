"""Services package avec dependency injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from labomatics.services.auth_service import AuthService
from labomatics.services.mail_service import MailService
from labomatics.services.student_import_service import StudentImportService
from labomatics.services.student_service import StudentService

__all__ = [
    "AuthService",
    "AuthServiceDep",
    "MailService",
    "MailServiceDep",
    "StudentService",
    "StudentServiceDep",
    "StudentImportService",
    "StudentImportServiceDep",
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


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
MailServiceDep = Annotated[MailService, Depends(get_mail_service)]
StudentServiceDep = Annotated[StudentService, Depends(get_student_service)]
StudentImportServiceDep = Annotated[
    StudentImportService, Depends(get_student_import_service)
]

"""Service pour les étudiants."""

from __future__ import annotations

from labomatics.api.dto.student import StudentListItemDTO, StudentListResponseDTO
from labomatics.core.db.repository.student import StudentRepository


class StudentService:
    """Service pour la gestion des étudiants."""

    def __init__(self, repo: StudentRepository | None = None) -> None:
        self.repo = repo or StudentRepository()

    async def list_students(
        self, page: int = 1, size: int = 20
    ) -> StudentListResponseDTO:
        """Liste les étudiants actifs avec pagination."""
        students, total = await self.repo.list_with_pagination(page, size)

        items = []
        for student in students:
            active_enrollment = next(
                (e for e in student.enrollments if e.end_date is None), None
            )
            cohort_name = active_enrollment.cohort.name if active_enrollment else "—"

            active_provisioning = next(
                (p for p in student.lab_provisioning if p.status != "deleting"), None
            )
            wan_ip = None
            vxlan_tag = None

            if active_provisioning:
                if active_provisioning.ip_allocation:
                    wan_ip = str(active_provisioning.ip_allocation.ip_address)
                if active_provisioning.vxlan_allocation:
                    vxlan_tag = active_provisioning.vxlan_allocation.vni

            items.append(
                StudentListItemDTO(
                    id=str(student.id),
                    login=student.login,
                    email=student.email,
                    first_name=student.first_name,
                    last_name=student.last_name,
                    cohort_name=cohort_name,
                    wan_ip=wan_ip,
                    vxlan_tag=vxlan_tag,
                )
            )

        total_pages = (total + size - 1) // size

        return StudentListResponseDTO(
            items=items,
            total_count=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

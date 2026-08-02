"""Service pour les étudiants."""

from __future__ import annotations

from uuid import UUID

from labomatics.api.dto.lab import LabDataDTO, LabVmDTO, StudentDTO
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

    async def get_lab_data(self, student_id: UUID | str) -> LabDataDTO | None:
        """Récupère les données du lab d'un étudiant."""
        if isinstance(student_id, str):
            student_id = UUID(student_id)

        student = await self.repo.get_by_id_for_lab(student_id)
        if not student:
            return None

        # Récupère le cohort_name depuis l'enrollment actif
        active_enrollment = next(
            (e for e in student.enrollments if e.end_date is None), None
        )
        cohort_name = active_enrollment.cohort.name if active_enrollment else "—"

        # Récupère l'allocation active (WAN IP et VXLAN)
        active_provisioning = next(
            (p for p in student.lab_provisioning if p.status != "deleting"), None
        )
        wan_ip = None
        vxlan_tag = None
        vms: list[LabVmDTO] = []

        if active_provisioning:
            # Charge les VMs
            for vm in active_provisioning.vms:
                vms.append(
                    LabVmDTO(
                        id=str(vm.id),
                        name=vm.name,
                        cluster_name=vm.cluster_name,
                        state=vm.state,
                        cores=vm.cores,
                        memory=vm.memory,
                        disk=vm.disk,
                        created_at=vm.created_at,
                        notes=vm.notes,
                    )
                )

            # Récupère WAN IP
            if active_provisioning.ip_allocation:
                wan_ip = str(active_provisioning.ip_allocation.ip_address)

            # Récupère VXLAN tag (VNI)
            if active_provisioning.vxlan_allocation:
                vxlan_tag = active_provisioning.vxlan_allocation.vni

        # Construis le DTO StudentDTO
        student_dto = StudentDTO(
            id=str(student.id),
            login=student.login,
            first_name=student.first_name,
            last_name=student.last_name,
            email=student.email,
            cohort_name=cohort_name,
            created_at=student.created_at,
        )

        return LabDataDTO(
            student=student_dto,
            vms=vms,
            wan_ip=wan_ip,
            vxlan_tag=vxlan_tag,
            openwrt_link=None,  # À implémenter plus tard
        )

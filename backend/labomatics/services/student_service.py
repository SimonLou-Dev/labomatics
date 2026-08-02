"""Service pour les étudiants."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from labomatics.api.dto.lab import LabDataDTO, LabVmDTO, StudentDTO
from labomatics.api.dto.student import (
    StudentImportItemDTO,
    StudentListItemDTO,
    StudentListResponseDTO,
)
from labomatics.core.db.models import Student
from labomatics.core.db.repository.student import StudentRepository
from labomatics.utils.login_helper import (
    generate_login,
    generate_password,
    get_school_year,
)

logger = logging.getLogger(__name__)


class StudentService:
    """Service pour la gestion des étudiants."""

    def __init__(
        self,
        repo: StudentRepository | None = None,
        keycloak_service: object | None = None,
        cohort_repo: object | None = None,
        enrollment_repo: object | None = None,
        mail_service: object | None = None,
    ) -> None:
        self.repo = repo or StudentRepository()
        # Lazy imports pour éviter les cycles
        self.keycloak_service = keycloak_service
        self.cohort_repo = cohort_repo
        self.enrollment_repo = enrollment_repo
        self.mail_service = mail_service

    async def list_students(
        self,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
        cohort: str | None = None,
    ) -> StudentListResponseDTO:
        """Liste les étudiants actifs avec pagination et filtres."""
        students, total = await self.repo.list_with_pagination(page, size)

        items = []
        now = datetime.now()
        for student in students:
            # Trouver enrollment actif (start_date <= now <= end_date)
            active_enrollment = next(
                (e for e in student.enrollments if e.start_date <= now <= e.end_date),
                None,
            )
            cohort_name = active_enrollment.cohort.name if active_enrollment else "—"

            # Appliquer les filtres
            if cohort and cohort_name != cohort:
                continue

            if search:
                search_lower = search.lower()
                if not (
                    student.first_name.lower().find(search_lower) >= 0
                    or student.last_name.lower().find(search_lower) >= 0
                    or student.email.lower().find(search_lower) >= 0
                    or (
                        student.lab_provisioning
                        and any(
                            p.ip_allocation
                            and search_lower in str(p.ip_allocation.ip_address)
                            for p in student.lab_provisioning
                        )
                    )
                ):
                    continue

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

        # Récupère le cohort_name depuis l'enrollment actif (dates valides)
        now = datetime.now()
        active_enrollment = next(
            (e for e in student.enrollments if e.start_date <= now <= e.end_date),
            None,
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

    async def create_student(self, data: StudentImportItemDTO) -> None:
        """Crée un étudiant: DB + Keycloak."""
        from labomatics.services.keycloak_service import KeycloakService

        login = generate_login(data.first_name, data.last_name)

        # 1. Créer le Student en DB
        student = Student(
            external_id=int(data.id),  # data.id du CSV (numérique)
            login=login,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            is_active=True,
        )

        try:
            student = await self.repo.add(student)
            logger.info(f"Student créé en DB: {login}")
        except Exception as e:
            logger.error(f"Erreur création Student en DB {login}: {e}")
            raise

        # 2. Trouver ou créer le Cohort + assigner au cluster par défaut
        cohort = None
        if data.cohort_name:
            try:
                if not self.cohort_repo:
                    from labomatics.core.db.repository.cohort import CohortRepository

                    self.cohort_repo = CohortRepository()

                # Get school year (year, start_date, end_date)
                school_year, _, _ = get_school_year()

                # Get or create cohort by name + year (idempotent)
                cohort = await self.cohort_repo.update_or_create(
                    filters={"name": data.cohort_name, "year": school_year},
                    defaults={"is_active": True},
                )
                logger.info(f"Cohort trouvé/créé: {data.cohort_name} ({school_year})")

                # Assigner le cohort au cluster par défaut
                from labomatics.core.db.repository.cluster import ClusterRepository
                from labomatics.core.db.repository.cohort_cluster import (
                    CohortClusterRepository,
                )

                cluster_repo = ClusterRepository()
                clusters = await cluster_repo.list()
                default_cluster = next(
                    (c for c in clusters if c.is_default_for_new_cohorts), None
                )

                if default_cluster:
                    cohort_cluster_repo = CohortClusterRepository()
                    await cohort_cluster_repo.update_or_create(
                        filters={
                            "cohort_id": cohort.id,
                            "cluster_id": default_cluster.id,
                        },
                        defaults={},
                    )
                    logger.info(
                        f"Cohort assigné au cluster par défaut: {data.cohort_name} -> {default_cluster.name}"
                    )

            except Exception as e:
                logger.error(f"Erreur gestion Cohort {data.cohort_name}: {e}")
                cohort = None

        # 3. Créer l'Enrollment (idempotent)
        if cohort:
            try:
                if not self.enrollment_repo:
                    from labomatics.core.db.repository.enrollment import (
                        EnrollmentRepository,
                    )

                    self.enrollment_repo = EnrollmentRepository()

                _, start_date, end_date = get_school_year()

                await self.enrollment_repo.update_or_create(
                    filters={
                        "student_id": student.id,
                        "cohort_id": cohort.id,
                    },
                    defaults={
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
                logger.info(f"Enrollment créé/trouvé: {login} -> {data.cohort_name}")
            except Exception as e:
                logger.error(f"Erreur création Enrollment pour {login}: {e}")

        # 4. Créer l'utilisateur en Keycloak + envoyer mail
        try:
            from labomatics.services.mail_service import MailService

            keycloak_svc = self.keycloak_service or KeycloakService()
            result = await keycloak_svc.create_user(
                login=login,
                email=data.email,
                first_name=data.first_name,
                last_name=data.last_name,
            )

            # Mettre à jour student avec le keycloak_user_id
            keycloak_user_id = None
            if isinstance(result, dict) and "id" in result:
                keycloak_user_id = (
                    UUID(result["id"])
                    if isinstance(result["id"], str)
                    else result["id"]
                )
            else:
                keycloak_user_id = result  # En cas de retour direct UUID

            await self.repo.update(student.id, {"keycloak_user_id": keycloak_user_id})
            logger.info(f"User créé en Keycloak: {login} ({keycloak_user_id})")

            # 5. Ajouter au groupe "student"
            await keycloak_svc.add_user_to_group(login=login, group_name="student")
            logger.info(f"User ajouté au groupe 'student': {login}")

            # 6. Générer password et le définir
            password = generate_password()
            await keycloak_svc.set_user_password(login=login, password=password)
            logger.info(f"Password défini pour {login}")

            # 7. Envoyer mail avec identifiants
            mail_svc = self.mail_service or MailService()
            subject = f"Accès laboratoire - {data.first_name} {data.last_name}"
            body = f"""Bonjour {data.first_name} {data.last_name},

Voici vos identifiants d'accès au laboratoire:

Login: {login}
Mot de passe: {password}

Veuillez changer votre mot de passe lors de votre première connexion.

Cordialement,
L'équipe du laboratoire"""

            await mail_svc.send_mail(to=data.email, subject=subject, body=body)
            logger.info(f"Mail d'accès envoyé à {data.email}")

        except Exception as e:
            logger.error(f"Erreur création Keycloak pour {login}: {e}")
            # Ne pas échouer le process complet si Keycloak échoue

    async def update_student(self, data: StudentImportItemDTO) -> None:
        """Met à jour un étudiant existant (login non modifiable)."""
        from labomatics.services.keycloak_service import KeycloakService

        # Récupérer le student
        student = await self.repo.get_by_external_id(int(data.id))
        if not student:
            logger.warning(f"Student introuvable (id={data.id})")
            return

        login = student.login  # Le login existant (ne pas le modifier)

        # Mettre à jour les champs
        old_email = student.email

        try:
            await self.repo.update(
                student.id,
                {
                    "first_name": data.first_name,
                    "last_name": data.last_name,
                    "email": data.email,
                },
            )
            logger.info(f"Student mis à jour en DB: {login}")
        except Exception as e:
            logger.error(f"Erreur mise à jour Student {login}: {e}")
            raise

        # Mettre à jour en Keycloak si l'email a changé
        if old_email != data.email and student.keycloak_user_id:
            try:
                keycloak_svc = self.keycloak_service or KeycloakService()
                await keycloak_svc.update_user(
                    login=login,
                    email=data.email,
                    first_name=data.first_name,
                    last_name=data.last_name,
                )
                logger.info(f"User mis à jour en Keycloak: {login}")
            except Exception as e:
                logger.warning(f"Erreur mise à jour Keycloak pour {login}: {e}")

    async def delete_student(self, data: StudentImportItemDTO) -> None:
        """Supprime un étudiant (soft delete + Keycloak)."""
        from labomatics.services.keycloak_service import KeycloakService

        # Récupérer le student
        student = await self.repo.get_by_external_id(int(data.id))
        if not student:
            logger.warning(f"Student introuvable pour suppression (id={data.id})")
            return

        login = student.login

        # Soft delete en DB
        try:
            await self.repo.update(
                student.id,
                {
                    "is_active": False,
                    "left_at": datetime.now(),
                },
            )
            logger.info(f"Student marqué inactif: {login}")
        except Exception as e:
            logger.error(f"Erreur suppression Student {login}: {e}")
            raise

        # Supprimer de Keycloak
        if student.keycloak_user_id:
            try:
                keycloak_svc = self.keycloak_service or KeycloakService()
                await keycloak_svc.delete_user(login=login)
                logger.info(f"User supprimé de Keycloak: {login}")
            except Exception as e:
                logger.warning(f"Erreur suppression Keycloak pour {login}: {e}")

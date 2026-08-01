"""Service d'import CSV d'étudiants."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from labomatics.api.dto.student_import import (
    StudentImportCreatedDTO,
    StudentImportDiffDTO,
    StudentImportMappingDTO,
    StudentImportRemovedDTO,
    StudentImportRowErrorDTO,
    StudentImportUpdatedDTO,
)
from labomatics.core.connectors.keycloak import KeycloakAdminConnector
from labomatics.core.db.models import Enrollment, LabProvisioning, Student
from labomatics.core.db.repository import (
    CohortRepository,
    EnrollmentRepository,
    LabProvisioningRepository,
    StudentRepository,
)
from labomatics.services.mail_service import MailService


class StudentImportService:
    """Service d'import CSV d'étudiants avec diff/apply."""

    def __init__(
        self,
        student_repo: StudentRepository | None = None,
        cohort_repo: CohortRepository | None = None,
        enrollment_repo: EnrollmentRepository | None = None,
        lab_provisioning_repo: LabProvisioningRepository | None = None,
        keycloak_connector: KeycloakAdminConnector | None = None,
        mail_service: MailService | None = None,
    ) -> None:
        """Initialise le service avec les dépendances."""
        self.student_repo = student_repo or StudentRepository()
        self.cohort_repo = cohort_repo or CohortRepository()
        self.enrollment_repo = enrollment_repo or EnrollmentRepository()
        self.lab_provisioning_repo = (
            lab_provisioning_repo or LabProvisioningRepository()
        )
        self.keycloak_connector = keycloak_connector or KeycloakAdminConnector()
        self.mail_service = mail_service or MailService()

    def _generate_login(self, first_name: str, last_name: str) -> str:
        """Génère le login selon la règle V0: prenom[0].lower() + nom.lower()."""
        prefix = first_name[0].lower() if first_name else ""
        return (prefix + last_name).lower()

    async def _validate_rows(
        self, rows: list[dict], mapping: StudentImportMappingDTO
    ) -> tuple[list[dict], list[StudentImportRowErrorDTO]]:
        """Valide toutes les lignes du CSV. Retourne (lignes_valides, erreurs)."""
        errors = []
        valid_rows = []

        for idx, row in enumerate(rows, start=1):
            # Vérifier les colonnes présentes
            if (
                mapping.external_id_column not in row
                or mapping.last_name_column not in row
                or mapping.first_name_column not in row
                or mapping.email_column not in row
                or mapping.cohort_column not in row
            ):
                errors.append(
                    StudentImportRowErrorDTO(
                        row_index=idx,
                        external_id=None,
                        reason="Colonnes manquantes dans le CSV",
                    )
                )
                continue

            # Valider external_id (entier)
            try:
                external_id = int(row[mapping.external_id_column])
            except ValueError:
                errors.append(
                    StudentImportRowErrorDTO(
                        row_index=idx,
                        external_id=row.get(mapping.external_id_column),
                        reason="external_id doit être un entier",
                    )
                )
                continue

            # Valider email (basique)
            email = row[mapping.email_column].strip()
            if "@" not in email:
                errors.append(
                    StudentImportRowErrorDTO(
                        row_index=idx,
                        external_id=row.get(mapping.external_id_column),
                        reason="Email invalide",
                    )
                )
                continue

            valid_rows.append(
                {
                    "external_id": external_id,
                    "last_name": row[mapping.last_name_column].strip(),
                    "first_name": row[mapping.first_name_column].strip(),
                    "email": email,
                    "cohort_name": row[mapping.cohort_column].strip(),
                }
            )

        return valid_rows, errors

    async def preview(
        self,
        rows: list[dict],
        mapping: StudentImportMappingDTO,
        year: int,
    ) -> StudentImportDiffDTO:
        """Calcule le diff sans appliquer aucune modification."""
        valid_rows, errors = await self._validate_rows(rows, mapping)

        if errors:
            return StudentImportDiffDTO(errors=errors)

        # Charger les étudiants actifs actuels
        current_students = {
            s.external_id: s for s in await self.student_repo.list_active()
        }

        # Catégoriser les lignes
        created = []
        updated = []
        removed_ids = set(current_students.keys())

        for row in valid_rows:
            eid = row["external_id"]
            removed_ids.discard(eid)

            if eid not in current_students:
                # Nouveau
                login = self._generate_login(row["first_name"], row["last_name"])
                created.append(
                    StudentImportCreatedDTO(
                        external_id=eid,
                        login=login,
                        email=row["email"],
                        cohort_name=row["cohort_name"],
                    )
                )
            else:
                # Vérifier si modifié
                student = current_students[eid]
                changes = {}
                if student.last_name != row["last_name"]:
                    changes["last_name"] = row["last_name"]
                if student.first_name != row["first_name"]:
                    changes["first_name"] = row["first_name"]
                if student.email != row["email"]:
                    changes["email"] = row["email"]

                if changes:
                    updated.append(
                        StudentImportUpdatedDTO(external_id=eid, changes=changes)
                    )

        # Supprimés (absent du nouveau CSV)
        removed = [
            StudentImportRemovedDTO(external_id=eid, login=current_students[eid].login)
            for eid in removed_ids
        ]

        return StudentImportDiffDTO(
            created=created, updated=updated, removed=removed, errors=errors
        )

    async def apply(
        self,
        rows: list[dict],
        mapping: StudentImportMappingDTO,
        year: int,
    ) -> StudentImportDiffDTO:
        """Applique l'import (création/modification/suppression)."""
        # Valider d'abord
        valid_rows, errors = await self._validate_rows(rows, mapping)

        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Erreurs de validation du CSV",
            )

        # Charger l'état actuel
        current_students = {
            s.external_id: s for s in await self.student_repo.list_active()
        }
        removed_ids = set(current_students.keys())

        created_list = []
        updated_list = []

        # Traiter chaque ligne
        for row in valid_rows:
            eid = row["external_id"]
            removed_ids.discard(eid)

            if eid not in current_students:
                # Créer le nouvel étudiant
                login = self._generate_login(row["first_name"], row["last_name"])

                # Vérifier collision sur login
                collision_count = 0
                base_login = login
                while await self.student_repo.get_by_login(login):
                    collision_count += 1
                    login = f"{base_login}{eid}"

                # Créer le compte Keycloak
                (
                    kc_user_id,
                    temp_password,
                ) = await self.keycloak_connector.create_student_user(
                    username=login,
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    email=row["email"],
                )

                # Créer ou récupérer la promo
                cohort = await self.cohort_repo.first_or_create(
                    name=row["cohort_name"],
                    defaults={"year": year},
                )

                # Créer l'étudiant
                student = Student(
                    external_id=eid,
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    email=row["email"],
                    login=login,
                    keycloak_user_id=kc_user_id,
                    is_active=True,
                )
                student = await self.student_repo.add(student)

                # Créer l'affectation
                enrollment = Enrollment(
                    student_id=student.id,
                    cohort_id=cohort.id,
                    start_date=datetime.utcnow(),
                )
                await self.enrollment_repo.add(enrollment)

                # Envoyer un mail (stub)
                await self.mail_service.send_mail(
                    to=row["email"],
                    subject="Compte créé - Labomatics",
                    body=(
                        f"Bienvenue, {row['first_name']}!\n"
                        f"Identifiant: {login}\n"
                        f"Mot de passe temporaire: {temp_password}\n"
                        f"Veuillez changer votre mot de passe à la première connexion."
                    ),
                )

                created_list.append(
                    StudentImportCreatedDTO(
                        external_id=eid,
                        login=login,
                        email=row["email"],
                        cohort_name=row["cohort_name"],
                    )
                )
            else:
                # Modifier l'étudiant existant
                student = current_students[eid]
                changes = {}

                if student.last_name != row["last_name"]:
                    student.last_name = row["last_name"]
                    changes["last_name"] = row["last_name"]
                if student.first_name != row["first_name"]:
                    student.first_name = row["first_name"]
                    changes["first_name"] = row["first_name"]
                if student.email != row["email"]:
                    student.email = row["email"]
                    changes["email"] = row["email"]

                if changes:
                    await self.student_repo.update(student.id, changes)

                    # Vérifier si la promo a changé
                    # (toujours utiliser l'enrollment actif, pas créer un nouveau)
                    active_enrollment = await self.enrollment_repo.first_or_create(
                        where=[
                            Enrollment.student_id == student.id,
                            Enrollment.end_date.is_(None),
                        ]
                    )

                    cohort = await self.cohort_repo.first_or_create(
                        name=row["cohort_name"],
                        defaults={"year": year},
                    )

                    if active_enrollment.cohort_id != cohort.id:
                        # Fermer l'ancien enrollment
                        await self.enrollment_repo.update(
                            active_enrollment.id, {"end_date": datetime.utcnow()}
                        )
                        # Créer un nouveau
                        new_enrollment = Enrollment(
                            student_id=student.id,
                            cohort_id=cohort.id,
                            start_date=datetime.utcnow(),
                        )
                        await self.enrollment_repo.add(new_enrollment)

                    updated_list.append(
                        StudentImportUpdatedDTO(external_id=eid, changes=changes)
                    )

        # Traiter les supprimés
        removed_list = []
        for eid in removed_ids:
            student = current_students[eid]
            await self.keycloak_connector.delete_user(student.keycloak_user_id)
            await self.student_repo.update(
                student.id,
                {"is_active": False, "left_at": datetime.utcnow()},
            )

            # Clôturer enrollment actif
            active_enrollment = await self.enrollment_repo.first_or_create(
                where=[
                    Enrollment.student_id == student.id,
                    Enrollment.end_date.is_(None),
                ]
            )
            if active_enrollment:
                await self.enrollment_repo.update(
                    active_enrollment.id, {"end_date": datetime.utcnow()}
                )

            # Marquer lab_provisioning en deleting
            for lab_prov in await self.lab_provisioning_repo.where(
                LabProvisioning.student_id == student.id
            ):
                if lab_prov.status != "deleted" and lab_prov.status != "deleting":
                    await self.lab_provisioning_repo.update(
                        lab_prov.id, {"status": "deleting"}
                    )

            removed_list.append(
                StudentImportRemovedDTO(external_id=eid, login=student.login)
            )

        return StudentImportDiffDTO(
            created=created_list, updated=updated_list, removed=removed_list
        )

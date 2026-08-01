"""Connecteur Keycloak Admin API (raw client, pas de logique métier)."""

from __future__ import annotations

import secrets

from keycloak import KeycloakAdmin

from labomatics.core.config.settings import settings


class KeycloakAdminConnector:
    """Connecteur pour l'API Admin de Keycloak."""

    def __init__(self) -> None:
        """Initialise le connecteur avec les creds du backend."""
        self.server_url = settings.keycloak_url.rstrip("/")
        self.realm_name = "labomatics"
        self.kc_admin = KeycloakAdmin(
            server_url=self.server_url,
            client_id="admin-cli",
            realm_name="master",
            username=settings.keycloak_admin_username,
            password=settings.keycloak_admin_password,
            verify=False,  # TODO: vérifier les certs en prod
        )

    async def create_student_user(
        self, username: str, first_name: str, last_name: str, email: str
    ) -> tuple[str, str]:
        """Crée un user Keycloak dans le groupe 'student' avec password temporaire.

        Retourne (keycloak_user_id, temporary_password).
        """
        temp_password = secrets.token_urlsafe(16)

        # Créer l'user
        user_id = self.kc_admin.create_user(
            payload={
                "username": username,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "credentials": [
                    {"type": "password", "value": temp_password, "temporary": True}
                ],
            },
            exist_ok=True,
        )

        # L'ajouter au groupe 'student'
        # Récupérer l'ID du groupe
        groups = self.kc_admin.get_groups(query={"realm-name": self.realm_name})
        student_group_id = None
        for group in groups:
            if group["name"] == "student":
                student_group_id = group["id"]
                break

        if student_group_id:
            self.kc_admin.group_user_add(user_id, student_group_id)

        return user_id, temp_password

    async def delete_user(self, keycloak_user_id: str) -> None:
        """Supprime un user Keycloak."""
        self.kc_admin.delete_user(keycloak_user_id)

"""Service pour gérer les users dans Keycloak."""

from __future__ import annotations

import logging

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from labomatics.core.config.settings import settings

logger = logging.getLogger(__name__)


class KeycloakService:
    """Service pour gérer les users Keycloak."""

    def __init__(self) -> None:
        self.admin_client = KeycloakAdmin(
            server_url=settings.keycloak_url,
            username=settings.keycloak_admin_username,
            password=settings.keycloak_admin_password,
            realm_name=settings.keycloak_realm,
            client_id="admin-cli",
            verify=False,
        )

    async def create_user(
        self, login: str, email: str, first_name: str, last_name: str
    ) -> dict:
        """Crée un user dans Keycloak."""
        try:
            user_id = self.admin_client.create_user(
                {
                    "username": login,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": True,
                }
            )
            logger.info(f"Created Keycloak user {login} with id {user_id}")
            return {"id": user_id, "username": login, "email": email}
        except KeycloakError as e:
            logger.error(f"Failed to create Keycloak user {login}: {e}")
            raise

    async def update_user(
        self, login: str, email: str, first_name: str, last_name: str
    ) -> dict:
        """Met à jour un user dans Keycloak."""
        try:
            user_id = self.admin_client.get_user_id(login)
            self.admin_client.update_user(
                user_id,
                {
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                },
            )
            logger.info(f"Updated Keycloak user {login}")
            return {"id": user_id, "username": login, "email": email}
        except KeycloakError as e:
            logger.error(f"Failed to update Keycloak user {login}: {e}")
            raise

    async def delete_user(self, login: str) -> bool:
        """Supprime un user de Keycloak."""
        try:
            user_id = self.admin_client.get_user_id(login)
            self.admin_client.delete_user(user_id)
            logger.info(f"Deleted Keycloak user {login}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to delete Keycloak user {login}: {e}")
            raise

    async def set_user_password(self, login: str, password: str) -> bool:
        """Définit le mot de passe d'un user."""
        try:
            user_id = self.admin_client.get_user_id(login)
            self.admin_client.set_user_password(user_id, password, temporary=False)
            logger.info(f"Set password for Keycloak user {login}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to set password for Keycloak user {login}: {e}")
            raise

    async def add_user_to_group(self, login: str, group_name: str) -> bool:
        """Ajoute un user à un groupe."""
        try:
            user_id = self.admin_client.get_user_id(login)
            # Trouver le groupe par nom
            groups = self.admin_client.get_groups()
            group_id = next((g["id"] for g in groups if g["name"] == group_name), None)
            if not group_id:
                logger.warning(f"Group {group_name} not found")
                return False

            self.admin_client.group_user_add(user_id, group_id)
            logger.info(f"Added user {login} to group {group_name}")
            return True
        except KeycloakError as e:
            logger.error(f"Failed to add user {login} to group {group_name}: {e}")
            raise

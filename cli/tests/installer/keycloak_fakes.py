"""Faux client Keycloak en mémoire pour tester les tâches."""

from __future__ import annotations

from typing import Any


class FakeKeycloak:
    """Imite `KeycloakApi` : état en mémoire, appels enregistrés dans `calls`."""

    def __init__(self) -> None:
        """Initialise un Keycloak vide."""
        self.calls: list[tuple] = []
        self.realm_settings: dict[str, Any] = {}
        self.groups: dict[str, str] = {}
        self.roles: set[str] = set()
        self.users: dict[str, str] = {}
        self.passwords: dict[str, tuple[str, bool]] = {}
        self.clients: dict[str, dict[str, Any]] = {}
        self.components: dict[str, dict[str, Any]] = {}

    def _rec(self, *call: Any) -> None:
        """Enregistre un appel.

        Args:
            *call: Nom de la méthode puis ses arguments.
        """
        self.calls.append(call)

    def names(self) -> list[str]:
        """Noms des méthodes appelées.

        Returns:
            Les noms, dans l'ordre.
        """
        return [c[0] for c in self.calls]

    def wait_ready(self) -> None:
        """Simule l'attente de Keycloak."""
        self._rec("wait_ready")

    def ensure_realm(self, name: str, settings: dict[str, Any]) -> str:
        """Crée ou met à jour le realm.

        Args:
            name: Nom.
            settings: Paramètres.

        Returns:
            Un identifiant fixe.
        """
        self._rec("ensure_realm", name)
        self.realm_settings = settings
        return "realm-id"

    def ensure_realm_role(
        self, realm: str, name: str, description: str = "", composite: bool = False
    ) -> None:
        """Enregistre un rôle.

        Args:
            realm: Realm.
            name: Rôle.
            description: Description.
            composite: Composite.
        """
        self.roles.add(name)

    def ensure_group(self, realm: str, name: str) -> str:
        """Enregistre un groupe.

        Args:
            realm: Realm.
            name: Groupe.

        Returns:
            Son identifiant.
        """
        return self.groups.setdefault(name, f"g-{name}")

    def add_role_to_group(self, realm: str, group_id: str, role: str) -> None:
        """Enregistre une association.

        Args:
            realm: Realm.
            group_id: Groupe.
            role: Rôle.
        """
        self._rec("add_role_to_group", group_id, role)

    def set_default_group(self, realm: str, group_id: str) -> None:
        """Enregistre le groupe par défaut.

        Args:
            realm: Realm.
            group_id: Groupe.
        """
        self._rec("set_default_group", group_id)

    def add_all_client_roles_to_role(self, realm: str, role: str) -> None:
        """Enregistre l'appel.

        Args:
            realm: Realm.
            role: Rôle.
        """
        self._rec("add_all_client_roles_to_role", role)

    def ensure_user(
        self, realm: str, username: str, attributes: dict[str, Any]
    ) -> tuple[str, bool]:
        """Crée un utilisateur.

        Args:
            realm: Realm.
            username: Identifiant.
            attributes: Profil.

        Returns:
            Son identifiant et s'il vient d'être créé.
        """
        created = username not in self.users
        self.users.setdefault(username, f"u-{username}")
        return self.users[username], created

    def has_password(self, realm: str, user_id: str) -> bool:
        """Mot de passe défini ?

        Args:
            realm: Realm.
            user_id: Utilisateur.

        Returns:
            True s'il a été posé.
        """
        return user_id in self.passwords

    def set_password(
        self, realm: str, user_id: str, password: str, temporary: bool
    ) -> None:
        """Pose un mot de passe.

        Args:
            realm: Realm.
            user_id: Utilisateur.
            password: Mot de passe.
            temporary: Temporaire.
        """
        self.passwords[user_id] = (password, temporary)

    def add_user_to_group(self, realm: str, user_id: str, group_id: str) -> None:
        """Enregistre l'appartenance.

        Args:
            realm: Realm.
            user_id: Utilisateur.
            group_id: Groupe.
        """
        self._rec("add_user_to_group", user_id, group_id)

    def assign_client_roles(
        self, realm: str, user_id: str, client_id: str, roles: list[str]
    ) -> None:
        """Enregistre l'affectation.

        Args:
            realm: Realm.
            user_id: Utilisateur.
            client_id: Client.
            roles: Rôles.
        """
        self._rec("assign_client_roles", user_id, client_id, tuple(roles))

    def ensure_client(
        self, realm: str, client_id: str, settings: dict[str, Any]
    ) -> str:
        """Crée ou met à jour un client.

        Args:
            realm: Realm.
            client_id: Client.
            settings: Paramètres.

        Returns:
            Son identifiant interne.
        """
        self.clients[client_id] = settings
        return f"c-{client_id}"

    def ensure_client_role(
        self, realm: str, client_uuid: str, name: str, description: str
    ) -> None:
        """Enregistre l'appel.

        Args:
            realm: Realm.
            client_uuid: Client.
            name: Rôle.
            description: Description.
        """
        self._rec("ensure_client_role", name)

    def client_secret(self, realm: str, client_uuid: str) -> str:
        """Secret du client.

        Args:
            realm: Realm.
            client_uuid: Client.

        Returns:
            Un secret dérivé de l'identifiant.
        """
        return f"secret-of-{client_uuid}"

    def ensure_component(self, realm: str, component: dict[str, Any]) -> str:
        """Crée ou met à jour un composant par nom.

        Args:
            realm: Realm.
            component: Représentation.

        Returns:
            Son identifiant.
        """
        self.components[component["name"]] = component
        return f"comp-{component['name']}"

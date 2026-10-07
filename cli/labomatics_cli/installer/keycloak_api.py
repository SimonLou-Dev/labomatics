"""Client minimal de l'API d'administration Keycloak."""

from __future__ import annotations

import time
from typing import Any, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REALM = "labomatics"
MASTER_TOKEN_PATH = "/realms/master/protocol/openid-connect/token"


class KeycloakError(Exception):
    """Erreur de l'API Keycloak, avec un message affichable."""


class KeycloakApi:
    """Appels d'administration Keycloak ; chaque méthode `ensure_*` crée ou met à jour."""

    def __init__(
        self,
        base_url: str,
        admin_user: str,
        admin_password: str,
        *,
        host: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
    ) -> None:
        """Prépare le client (aucune requête n'est envoyée).

        Args:
            base_url: URL de Keycloak (ex. `https://192.168.50.10`).
            admin_user: Administrateur du realm master.
            admin_password: Son mot de passe.
            host: En-tête `Host` à envoyer (Traefik route sur le nom, pas sur l'IP).
            session: Session HTTP, remplaçable en test.
            timeout: Délai maximal par requête en secondes.
        """
        self.base_url = base_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.verify = False
        if host:
            self._session.headers["Host"] = host
        self._token: Optional[str] = None

    def login(self) -> None:
        """Obtient un jeton d'administration.

        Raises:
            KeycloakError: Si l'authentification échoue ou que Keycloak est injoignable.
        """
        try:
            response = self._session.post(
                self.base_url + MASTER_TOKEN_PATH,
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": self.admin_user,
                    "password": self.admin_password,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise KeycloakError(f"Keycloak injoignable : {exc}") from exc
        if response.status_code != 200:
            raise KeycloakError(
                f"Authentification Keycloak refusée ({response.status_code})"
            )
        self._token = response.json()["access_token"]

    def wait_ready(self, attempts: int = 60, delay: float = 5.0) -> None:
        """Attend que Keycloak accepte l'authentification.

        Args:
            attempts: Nombre maximal de tentatives.
            delay: Pause entre deux tentatives en secondes.

        Raises:
            KeycloakError: Si Keycloak ne répond pas après toutes les tentatives.
        """
        for attempt in range(attempts):
            try:
                self.login()
                return
            except KeycloakError as exc:
                if attempt == attempts - 1:
                    raise exc
                time.sleep(delay)

    def _request(
        self, method: str, path: str, *, ok: tuple[int, ...] = (), **kwargs: Any
    ) -> requests.Response:
        """Envoie une requête d'administration, en se réauthentifiant si le jeton a expiré.

        Args:
            method: Méthode HTTP.
            path: Chemin sous `/admin/realms`.
            ok: Codes d'erreur acceptés (ex. 404 pour « absent »).
            **kwargs: Arguments de `requests` (json, params…).

        Returns:
            La réponse.

        Raises:
            KeycloakError: Si la réponse est une erreur non acceptée.
        """
        url = f"{self.base_url}/admin/realms{path}"
        for attempt in range(2):
            if self._token is None:
                self.login()
            try:
                response = self._session.request(
                    method,
                    url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                raise KeycloakError(f"Keycloak injoignable : {exc}") from exc
            if response.status_code == 401 and attempt == 0:
                self._token = None
                continue
            break
        if response.status_code >= 400 and response.status_code not in ok:
            raise KeycloakError(
                f"{method} {path} : {response.status_code} {response.text[:200]}"
            )
        return response

    @staticmethod
    def _created_id(response: requests.Response) -> str:
        """Extrait l'identifiant d'une ressource créée.

        Args:
            response: Réponse 201 de Keycloak.

        Returns:
            Le dernier segment de l'en-tête `Location`.
        """
        return response.headers.get("Location", "").rstrip("/").split("/")[-1]

    def realm(self, name: str) -> Optional[dict[str, Any]]:
        """Lit un realm.

        Args:
            name: Nom du realm.

        Returns:
            Sa représentation, ou None s'il n'existe pas.
        """
        response = self._request("GET", f"/{name}", ok=(404,))
        return None if response.status_code == 404 else response.json()

    def ensure_realm(self, name: str, settings: dict[str, Any]) -> str:
        """Crée le realm ou met à jour ses paramètres.

        Args:
            name: Nom du realm.
            settings: Paramètres à appliquer (politique de mots de passe, SMTP…).

        Returns:
            L'identifiant interne du realm.
        """
        current = self.realm(name)
        if current is None:
            self._request("POST", "", json={"realm": name, "enabled": True, **settings})
            current = self.realm(name) or {}
        else:
            current = {**current, **settings}
            self._request("PUT", f"/{name}", json=current)
        return str(current["id"])

    def ensure_group(self, realm: str, name: str) -> str:
        """Crée un groupe racine s'il n'existe pas.

        Args:
            realm: Nom du realm.
            name: Nom du groupe.

        Returns:
            L'identifiant du groupe.
        """
        groups = self._request(
            "GET", f"/{realm}/groups", params={"search": name, "exact": "true"}
        ).json()
        for group in groups:
            if group["name"] == name:
                return str(group["id"])
        response = self._request("POST", f"/{realm}/groups", json={"name": name})
        return self._created_id(response)

    def set_default_group(self, realm: str, group_id: str) -> None:
        """Ajoute un groupe aux groupes par défaut des nouveaux utilisateurs.

        Args:
            realm: Nom du realm.
            group_id: Identifiant du groupe.
        """
        self._request("PUT", f"/{realm}/default-groups/{group_id}")

    def ensure_realm_role(
        self, realm: str, name: str, description: str = "", composite: bool = False
    ) -> None:
        """Crée un rôle de realm s'il n'existe pas.

        Args:
            realm: Nom du realm.
            name: Nom du rôle.
            description: Description du rôle.
            composite: Rôle composite (regroupe d'autres rôles).
        """
        body = {"name": name, "description": description, "composite": composite}
        response = self._request("POST", f"/{realm}/roles", json=body, ok=(409,))
        if response.status_code == 409:
            self._request("PUT", f"/{realm}/roles/{name}", json=body)

    def add_role_to_group(self, realm: str, group_id: str, role: str) -> None:
        """Affecte un rôle de realm à un groupe.

        Args:
            realm: Nom du realm.
            group_id: Identifiant du groupe.
            role: Nom du rôle.
        """
        representation = self._request("GET", f"/{realm}/roles/{role}").json()
        self._request(
            "POST",
            f"/{realm}/groups/{group_id}/role-mappings/realm",
            json=[representation],
        )

    def add_all_client_roles_to_role(self, realm: str, role: str) -> None:
        """Rend un rôle composite de tous les rôles de tous les clients.

        Args:
            realm: Nom du realm.
            role: Nom du rôle composite.
        """
        collected: list[dict[str, Any]] = []
        clients = self._request(
            "GET", f"/{realm}/clients", params={"first": 0, "max": 100}
        ).json()
        for client in clients:
            collected += self._request(
                "GET", f"/{realm}/clients/{client['id']}/roles", params={"max": 200}
            ).json()
        if collected:
            self._request("POST", f"/{realm}/roles/{role}/composites", json=collected)

    def find_user(self, realm: str, username: str) -> Optional[dict[str, Any]]:
        """Cherche un utilisateur par identifiant exact.

        Args:
            realm: Nom du realm.
            username: Identifiant de connexion.

        Returns:
            Sa représentation, ou None.
        """
        users = self._request(
            "GET", f"/{realm}/users", params={"username": username, "exact": "true"}
        ).json()
        return users[0] if users else None

    def ensure_user(
        self, realm: str, username: str, attributes: dict[str, Any]
    ) -> tuple[str, bool]:
        """Crée un utilisateur ou met à jour son profil.

        Args:
            realm: Nom du realm.
            username: Identifiant de connexion.
            attributes: Prénom, nom, e-mail…

        Returns:
            L'identifiant de l'utilisateur et True s'il vient d'être créé.
        """
        existing = self.find_user(realm, username)
        if existing is not None:
            self._request(
                "PUT",
                f"/{realm}/users/{existing['id']}",
                json={**existing, **attributes},
            )
            return str(existing["id"]), False
        body = {"username": username, "enabled": True, **attributes}
        response = self._request("POST", f"/{realm}/users", json=body)
        return self._created_id(response), True

    def delete_user(self, realm: str, username: str) -> bool:
        """Supprime un utilisateur s'il existe.

        Args:
            realm: Nom du realm.
            username: Identifiant de connexion.

        Returns:
            True si un utilisateur a été supprimé.
        """
        existing = self.find_user(realm, username)
        if existing is None:
            return False
        self._request("DELETE", f"/{realm}/users/{existing['id']}")
        return True

    def has_password(self, realm: str, user_id: str) -> bool:
        """Indique si l'utilisateur a déjà un mot de passe.

        Args:
            realm: Nom du realm.
            user_id: Identifiant de l'utilisateur.

        Returns:
            True si un identifiant de type mot de passe existe.
        """
        credentials = self._request(
            "GET", f"/{realm}/users/{user_id}/credentials"
        ).json()
        return any(c.get("type") == "password" for c in credentials)

    def set_password(
        self, realm: str, user_id: str, password: str, temporary: bool
    ) -> None:
        """Définit le mot de passe d'un utilisateur.

        Args:
            realm: Nom du realm.
            user_id: Identifiant de l'utilisateur.
            password: Nouveau mot de passe.
            temporary: Oblige à le changer à la première connexion.
        """
        self._request(
            "PUT",
            f"/{realm}/users/{user_id}/reset-password",
            json={"type": "password", "value": password, "temporary": temporary},
        )

    def add_user_to_group(self, realm: str, user_id: str, group_id: str) -> None:
        """Ajoute un utilisateur à un groupe.

        Args:
            realm: Nom du realm.
            user_id: Identifiant de l'utilisateur.
            group_id: Identifiant du groupe.
        """
        self._request("PUT", f"/{realm}/users/{user_id}/groups/{group_id}")

    def find_client(self, realm: str, client_id: str) -> Optional[dict[str, Any]]:
        """Cherche un client par son `clientId`.

        Args:
            realm: Nom du realm.
            client_id: Identifiant public du client.

        Returns:
            Sa représentation, ou None.
        """
        clients = self._request(
            "GET", f"/{realm}/clients", params={"clientId": client_id}
        ).json()
        return clients[0] if clients else None

    def ensure_client(
        self, realm: str, client_id: str, settings: dict[str, Any]
    ) -> str:
        """Crée un client OIDC confidentiel ou met à jour ses paramètres.

        Args:
            realm: Nom du realm.
            client_id: Identifiant public du client.
            settings: Nom, URI de redirection, options…

        Returns:
            L'identifiant interne du client.
        """
        body = {
            "clientId": client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            **settings,
        }
        existing = self.find_client(realm, client_id)
        if existing is not None:
            self._request(
                "PUT", f"/{realm}/clients/{existing['id']}", json={**existing, **body}
            )
            return str(existing["id"])
        return self._created_id(self._request("POST", f"/{realm}/clients", json=body))

    def client_secret(self, realm: str, client_uuid: str) -> str:
        """Lit le secret d'un client confidentiel.

        Args:
            realm: Nom du realm.
            client_uuid: Identifiant interne du client.

        Returns:
            Le secret du client.
        """
        data = self._request(
            "GET", f"/{realm}/clients/{client_uuid}/client-secret"
        ).json()
        return str(data["value"])

    def service_account_user(self, realm: str, client_uuid: str) -> str:
        """Identifiant de l'utilisateur de compte de service d'un client.

        Args:
            realm: Nom du realm.
            client_uuid: Identifiant interne du client (comptes de service activés).

        Returns:
            L'identifiant de l'utilisateur `service-account-<client>`.
        """
        data = self._request(
            "GET", f"/{realm}/clients/{client_uuid}/service-account-user"
        ).json()
        return str(data["id"])

    def ensure_client_role(
        self, realm: str, client_uuid: str, name: str, description: str
    ) -> None:
        """Crée un rôle de client s'il n'existe pas.

        Args:
            realm: Nom du realm.
            client_uuid: Identifiant interne du client.
            name: Nom du rôle.
            description: Description du rôle.
        """
        self._request(
            "POST",
            f"/{realm}/clients/{client_uuid}/roles",
            json={"name": name, "description": description},
            ok=(409,),
        )

    def assign_client_roles(
        self, realm: str, user_id: str, client_id: str, roles: list[str]
    ) -> None:
        """Affecte des rôles d'un client à un utilisateur.

        Args:
            realm: Nom du realm.
            user_id: Identifiant de l'utilisateur.
            client_id: Identifiant public du client (ex. `realm-management`).
            roles: Noms des rôles.

        Raises:
            KeycloakError: Si le client ou un rôle est introuvable.
        """
        client = self.find_client(realm, client_id)
        if client is None:
            raise KeycloakError(f"Client {client_id} introuvable")
        available = {
            r["name"]: r
            for r in self._request(
                "GET", f"/{realm}/clients/{client['id']}/roles", params={"max": 200}
            ).json()
        }
        missing = [r for r in roles if r not in available]
        if missing:
            raise KeycloakError(f"Rôles introuvables dans {client_id} : {missing}")
        self._request(
            "POST",
            f"/{realm}/users/{user_id}/role-mappings/clients/{client['id']}",
            json=[available[r] for r in roles],
        )

    def ensure_component(self, realm: str, component: dict[str, Any]) -> str:
        """Crée un composant (fédération, mapper) ou le met à jour, identifié par son nom.

        Args:
            realm: Nom du realm.
            component: Représentation avec `name`, `providerType` et `parentId`.

        Returns:
            L'identifiant du composant.
        """
        found = self._request(
            "GET",
            f"/{realm}/components",
            params={"parent": component["parentId"], "type": component["providerType"]},
        ).json()
        for item in found:
            if item["name"] == component["name"]:
                body = {**item, **component, "id": item["id"]}
                self._request("PUT", f"/{realm}/components/{item['id']}", json=body)
                return str(item["id"])
        return self._created_id(
            self._request("POST", f"/{realm}/components", json=component)
        )

"""API Keycloak client pour setup."""

import requests
from typing import Optional, Dict, Any


class KeycloakClient:
    """Client Keycloak pour gestion realms, users, clients."""

    def __init__(self, base_url: str, admin_user: str, admin_password: str, realm: str = "master"):
        """Initialiser le client."""
        self.base_url = base_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.realm = realm
        self.token = None

    def auth(self) -> None:
        """S'authentifier et récupérer le token."""
        url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_user,
            "password": self.admin_password,
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        self.token = resp.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        """Headers pour les requêtes authentifiées."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def create_realm(self, realm_name: str) -> None:
        """Créer un realm."""
        url = f"{self.base_url}/admin/realms"
        data = {
            "realm": realm_name,
            "enabled": True,
        }
        requests.post(url, json=data, headers=self._headers()).raise_for_status()

    def create_client(self, realm_name: str, client_id: str, redirect_uris: list) -> str:
        """Créer un client OIDC et retourner le client secret."""
        url = f"{self.base_url}/admin/realms/{realm_name}/clients"
        data = {
            "clientId": client_id,
            "enabled": True,
            "publicClient": False,
            "redirectUris": redirect_uris,
            "protocol": "openid-connect",
            "attributes": {
                "oidc.compliance.subtle.change": "true",
            },
        }
        resp = requests.post(url, json=data, headers=self._headers())
        resp.raise_for_status()
        client_uuid = resp.json()["id"]

        # Récupérer le secret
        url_secret = f"{self.base_url}/admin/realms/{realm_name}/clients/{client_uuid}/client-secret"
        resp = requests.get(url_secret, headers=self._headers())
        resp.raise_for_status()
        return resp.json()["value"]

    def create_group(self, realm_name: str, group_name: str) -> str:
        """Créer un groupe et retourner son ID."""
        url = f"{self.base_url}/admin/realms/{realm_name}/groups"
        data = {"name": group_name}
        resp = requests.post(url, json=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()["id"]

    def create_user(self, realm_name: str, username: str, email: str, first_name: str, 
                    last_name: str, temporary_password: str) -> str:
        """Créer un user et retourner son ID."""
        url = f"{self.base_url}/admin/realms/{realm_name}/users"
        data = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "credentials": [
                {
                    "type": "password",
                    "value": temporary_password,
                    "temporary": True,
                }
            ],
        }
        resp = requests.post(url, json=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()["id"]

    def add_user_to_group(self, realm_name: str, user_id: str, group_id: str) -> None:
        """Ajouter un user à un groupe."""
        url = f"{self.base_url}/admin/realms/{realm_name}/users/{user_id}/groups/{group_id}"
        requests.put(url, headers=self._headers()).raise_for_status()

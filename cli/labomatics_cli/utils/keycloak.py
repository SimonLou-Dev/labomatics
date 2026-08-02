"""API Keycloak client pour setup."""

import requests
from typing import Dict


class KeycloakClient:
    """Client Keycloak pour gestion realms, users, clients."""

    def __init__(
        self, base_url: str, admin_user: str, admin_password: str, realm: str = "master"
    ):
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
        resp = requests.post(url, data=data, verify=False)
        try:
            resp.raise_for_status()
            self.token = resp.json()["access_token"]
        except Exception as e:
            raise RuntimeError(
                f"Keycloak auth failed: {resp.status_code} - {resp.text}"
            ) from e

    def _headers(self) -> Dict[str, str]:
        """Headers pour les requêtes authentifiées."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def create_realm(self, realm_name: str, display_name: str = None) -> None:
        """Créer un realm."""
        url = f"{self.base_url}/admin/realms"
        data = {
            "realm": realm_name,
            "displayName": display_name or realm_name,
            "enabled": True,
        }
        resp = requests.post(url, json=data, headers=self._headers(), verify=False)
        if resp.status_code == 409:
            return  # Realm exists, ignore
        resp.raise_for_status()

    def create_client(
        self,
        realm_name: str,
        client_id: str,
        name: str = None,
        redirect_uris: list = None,
        public_client: bool = False,
        enable_auth: bool = False,
    ) -> str:
        """Créer un client OIDC et retourner le client secret (ou vide pour clients publics)."""
        url = f"{self.base_url}/admin/realms/{realm_name}/clients"
        data = {
            "clientId": client_id,
            "name": name or client_id,
            "enabled": True,
            "publicClient": public_client,
            "authorizationServicesEnabled": enable_auth,
            "redirectUris": redirect_uris or [],
            "protocol": "openid-connect",
            "attributes": {
                "oidc.compliance.subtle.change": "true",
            },
        }
        resp = requests.post(url, json=data, headers=self._headers(), verify=False)
        if resp.status_code == 409:
            # Client exists, get its ID and secret
            clients = requests.get(
                f"{url}?clientId={client_id}", headers=self._headers(), verify=False
            ).json()
            if clients:
                client_uuid = clients[0]["id"]
        else:
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Failed to create client ({resp.status_code}): "
                    f"text='{resp.text}' | content='{resp.content}'"
                )
            try:
                if not resp.text:
                    # Empty response but status 201/200 - client was created but no body returned
                    # Try to fetch it
                    clients = requests.get(
                        f"{url}?clientId={client_id}",
                        headers=self._headers(),
                        verify=False,
                    ).json()
                    if clients:
                        client_uuid = clients[0]["id"]
                    else:
                        raise RuntimeError("Client created but not found in list")
                else:
                    client_uuid = resp.json()["id"]
            except Exception as e:
                raise RuntimeError(
                    f"Failed to parse client response: {resp.text}"
                ) from e

        # Les clients publics n'ont pas de secret
        if public_client:
            return ""

        # Récupérer le secret pour les clients confidentiels
        url_secret = f"{self.base_url}/admin/realms/{realm_name}/clients/{client_uuid}/client-secret"
        resp = requests.get(url_secret, headers=self._headers(), verify=False)
        resp.raise_for_status()
        try:
            return resp.json()["value"]
        except Exception as e:
            raise RuntimeError(f"Failed to get client secret: {resp.text}") from e

    def create_group(self, realm_name: str, group_name: str) -> str:
        """Créer un groupe et retourner son ID."""
        url = f"{self.base_url}/admin/realms/{realm_name}/groups"
        data = {"name": group_name}
        resp = requests.post(url, json=data, headers=self._headers(), verify=False)
        if resp.status_code == 409:
            # Group exists, get its ID
            groups = requests.get(url, headers=self._headers(), verify=False).json()
            for g in groups:
                if g["name"] == group_name:
                    return g["id"]
        try:
            resp.raise_for_status()
            # 201 Created: extract ID from Location header
            if resp.status_code == 201:
                location = resp.headers.get("Location", "")
                if location:
                    return location.split("/")[-1]
            return resp.json()["id"]
        except Exception as e:
            raise RuntimeError(
                f"create_group failed: {resp.status_code} - {resp.text}"
            ) from e

    def create_user(
        self,
        realm_name: str,
        username: str,
        first_name: str = "",
        last_name: str = "",
        email: str = None,
        temporary_password: str = None,
    ) -> str:
        """Créer un user et retourner son ID."""
        url = f"{self.base_url}/admin/realms/{realm_name}/users"
        data = {
            "username": username,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
        }

        if email:
            data["email"] = email

        if temporary_password:
            data["credentials"] = [
                {
                    "type": "password",
                    "value": temporary_password,
                    "temporary": True,
                }
            ]

        resp = requests.post(url, json=data, headers=self._headers(), verify=False)
        if resp.status_code == 409:
            # User exists, get its ID
            users = requests.get(
                f"{url}?username={username}", headers=self._headers(), verify=False
            ).json()
            if users:
                return users[0]["id"]
        try:
            resp.raise_for_status()
            # 201 Created: extract ID from Location header (e.g., .../users/{id})
            if resp.status_code == 201:
                location = resp.headers.get("Location", "")
                if location:
                    return location.split("/")[-1]
            return resp.json()["id"]
        except Exception as e:
            raise RuntimeError(
                f"create_user failed: {resp.status_code} - {resp.text}"
            ) from e

    def get_user_by_username(self, realm_name: str, username: str) -> dict | None:
        """Récupérer un user par username. Retourne None si pas trouvé."""
        url = f"{self.base_url}/admin/realms/{realm_name}/users?username={username}"
        resp = requests.get(url, headers=self._headers(), verify=False)
        resp.raise_for_status()
        users = resp.json()
        return users[0] if users else None

    def add_user_to_group(self, realm_name: str, user_id: str, group_id: str) -> None:
        """Ajouter un user à un groupe."""
        url = f"{self.base_url}/admin/realms/{realm_name}/users/{user_id}/groups/{group_id}"
        requests.put(url, headers=self._headers(), verify=False).raise_for_status()

    def set_user_password(
        self, realm_name: str, user_id: str, password: str, temporary: bool = False
    ) -> None:
        """Setter le password d'un user."""
        url = (
            f"{self.base_url}/admin/realms/{realm_name}/users/{user_id}/reset-password"
        )
        data = {"type": "password", "value": password, "temporary": temporary}
        requests.put(
            url, json=data, headers=self._headers(), verify=False
        ).raise_for_status()

    def create_realm_role(
        self,
        realm_name: str,
        role_name: str,
        description: str = None,
        composite: bool = False,
    ) -> str:
        """Créer un rôle realm et retourner son ID."""
        url = f"{self.base_url}/admin/realms/{realm_name}/roles"
        data = {
            "name": role_name,
            "description": description or role_name,
            "composite": composite,
        }
        resp = requests.post(url, json=data, headers=self._headers(), verify=False)

        if resp.status_code == 409:
            # Role exists, get its ID
            roles_url = f"{self.base_url}/admin/realms/{realm_name}/roles/{role_name}"
            role_data = requests.get(
                roles_url, headers=self._headers(), verify=False
            ).json()
            return role_data["id"]

        if resp.status_code == 201:
            location = resp.headers.get("Location", "")
            if location:
                return location.split("/")[-1]

        resp.raise_for_status()
        return resp.json()["id"]

    def add_composite_roles_to_role(
        self,
        realm_name: str,
        role_name: str,
        client_id: str,
        client_role_names: list,
    ) -> None:
        """Ajouter des rôles client à un rôle composite."""
        # Récupérer l'ID du client
        clients_url = f"{self.base_url}/admin/realms/{realm_name}/clients"
        clients = requests.get(
            clients_url, headers=self._headers(), verify=False
        ).json()
        client_obj_id = None
        for client in clients:
            if client["clientId"] == client_id:
                client_obj_id = client["id"]
                break

        if not client_obj_id:
            raise RuntimeError(f"Client {client_id} not found")

        # Récupérer les rôles du client avec filtre
        roles_url = f"{self.base_url}/admin/realms/{realm_name}/clients/{client_obj_id}/roles?first=0&max=100"
        roles = requests.get(roles_url, headers=self._headers(), verify=False).json()

        # Trouver les IDs des rôles à ajouter
        roles_to_add = []
        for role_name_to_add in client_role_names:
            found = False
            for role in roles:
                if role["name"] == role_name_to_add:
                    roles_to_add.append(
                        {
                            "id": role["id"],
                            "name": role["name"],
                            "clientRole": True,
                            "containerId": client_obj_id,
                        }
                    )
                    found = True
                    break
            if not found:
                raise RuntimeError(
                    f"Role '{role_name_to_add}' not found in client {client_id}"
                )

        # Ajouter les rôles au rôle composite
        url = f"{self.base_url}/admin/realms/{realm_name}/roles/{role_name}/composites"
        resp = requests.post(
            url, json=roles_to_add, headers=self._headers(), verify=False
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to add composite roles: {resp.status_code} - {resp.text}"
            )

    def add_all_client_roles_to_role(self, realm_name: str, role_name: str) -> None:
        """Ajouter tous les rôles de tous les clients à un rôle composite."""
        # Récupérer tous les clients
        clients_url = (
            f"{self.base_url}/admin/realms/{realm_name}/clients?first=0&max=100"
        )
        clients = requests.get(
            clients_url, headers=self._headers(), verify=False
        ).json()

        roles_to_add = []

        # Pour chaque client, récupérer tous ses rôles
        for client in clients:
            client_id = client["id"]
            roles_url = f"{self.base_url}/admin/realms/{realm_name}/clients/{client_id}/roles?first=0&max=100"
            roles = requests.get(
                roles_url, headers=self._headers(), verify=False
            ).json()

            # Ajouter tous les rôles du client
            for role in roles:
                roles_to_add.append(
                    {
                        "id": role["id"],
                        "name": role["name"],
                        "clientRole": True,
                        "containerId": client_id,
                    }
                )

        if not roles_to_add:
            raise RuntimeError("No client roles found")

        # Ajouter tous les rôles au rôle composite
        url = f"{self.base_url}/admin/realms/{realm_name}/roles/{role_name}/composites"
        resp = requests.post(
            url, json=roles_to_add, headers=self._headers(), verify=False
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to add composite roles: {resp.status_code} - {resp.text}"
            )

    def add_realm_role_to_group(
        self, realm_name: str, group_id: str, role_name: str
    ) -> None:
        """Assigner un rôle realm au groupe."""
        # D'abord récupérer l'ID du rôle
        roles_url = f"{self.base_url}/admin/realms/{realm_name}/roles"
        resp = requests.get(roles_url, headers=self._headers(), verify=False)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch roles: {resp.status_code} - {resp.text}"
            )
        roles = resp.json()

        role_id = None
        for role in roles:
            if role["name"] == role_name:
                role_id = role["id"]
                break

        if not role_id:
            available = ", ".join([r.get("name", "?") for r in roles[:5]])
            raise RuntimeError(
                f"Rôle '{role_name}' non trouvé. Rôles disponibles: {available}"
            )

        # Assigner le rôle au groupe
        url = f"{self.base_url}/admin/realms/{realm_name}/groups/{group_id}/role-mappings/realm"
        data = [{"id": role_id, "name": role_name}]
        resp = requests.post(url, json=data, headers=self._headers(), verify=False)
        if resp.status_code not in (204, 201, 200):
            raise RuntimeError(
                f"Failed to assign role: {resp.status_code} - {resp.text}"
            )

    def set_default_group(self, realm_name: str, group_id: str) -> None:
        """Définir un groupe comme groupe par défaut pour le realm."""
        url = f"{self.base_url}/admin/realms/{realm_name}"
        # Récupérer la config actuelle du realm
        realm_config = requests.get(url, headers=self._headers(), verify=False).json()
        # Modifier uniquement les default groups
        realm_config["defaultGroups"] = [f"/groups/{group_id}"]
        # Mettre à jour avec PUT (pas d'overwrite complet, juste les champs fournis)
        resp = requests.put(
            url, json=realm_config, headers=self._headers(), verify=False
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to set default group: {resp.status_code} - {resp.text}"
            )
        resp.raise_for_status()

    def get_client_uuid(self, realm_name: str, client_id: str) -> str:
        """Récupère l'UUID d'un client par son ID (ex: realm-management)."""
        url = f"{self.base_url}/admin/realms/{realm_name}/clients"
        clients = requests.get(
            f"{url}?clientId={client_id}", headers=self._headers(), verify=False
        ).json()
        if not clients:
            raise RuntimeError(f"Client {client_id} not found in realm {realm_name}")
        return clients[0]["id"]

    def create_client_role(
        self, realm_name: str, client_id: str, role_name: str, description: str = None
    ) -> str:
        """Créer un rôle client et retourner son ID."""
        client_uuid = self.get_client_uuid(realm_name, client_id)
        url = f"{self.base_url}/admin/realms/{realm_name}/clients/{client_uuid}/roles"
        data = {
            "name": role_name,
            "description": description or role_name,
        }
        resp = requests.post(url, json=data, headers=self._headers(), verify=False)

        if resp.status_code == 409:
            # Role exists, get its ID
            roles = requests.get(url, headers=self._headers(), verify=False).json()
            for role in roles:
                if role["name"] == role_name:
                    return role["id"]

        if resp.status_code == 201:
            location = resp.headers.get("Location", "")
            if location:
                return location.split("/")[-1]

        resp.raise_for_status()
        return resp.json()["id"]

    def assign_client_role_to_user(
        self, realm_name: str, user_id: str, client_id: str, role_name: str
    ) -> None:
        """Assigne un rôle client à un user."""
        # Récupérer l'UUID du client
        client_uuid = self.get_client_uuid(realm_name, client_id)

        # Récupérer les rôles du client
        roles_url = (
            f"{self.base_url}/admin/realms/{realm_name}/clients/{client_uuid}/roles"
        )
        roles = requests.get(roles_url, headers=self._headers(), verify=False).json()

        # Trouver le rôle
        role_obj = None
        for role in roles:
            if role["name"] == role_name:
                role_obj = role
                break

        if not role_obj:
            raise RuntimeError(f"Role '{role_name}' not found in client {client_id}")

        # Assigner le rôle au user
        url = f"{self.base_url}/admin/realms/{realm_name}/users/{user_id}/role-mappings/clients/{client_uuid}"
        resp = requests.post(
            url,
            json=[role_obj],
            headers=self._headers(),
            verify=False,
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to assign role: {resp.status_code} - {resp.text}"
            )

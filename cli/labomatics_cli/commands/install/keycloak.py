"""Keycloak setup."""

import secrets

from ...utils.keycloak import KeycloakClient
from ...utils.verify import ServiceVerifier
from ...utils.state import InstallState
from ...utils.theme import info, success, warning


class KeycloakSetup:
    """Configuration Keycloak."""

    def __init__(self, domain: str, admin_password: str, state: InstallState, pve=None):
        """Initialiser."""
        self.domain = domain
        self.admin_password = admin_password
        self.state = state
        self.pve = pve
        self.kc_url = f"https://keycloak.{domain}"

    def setup(self, admin_first_name: str, admin_last_name: str, admin_email: str):
        """Configurer Keycloak."""
        info(f"Attente Keycloak ({self.kc_url}/admin/labomatics/console/)...")
        ServiceVerifier.wait_for_http(
            f"{self.kc_url}/admin/labomatics/console/", timeout=300
        )
        success("Keycloak prêt")

        info("Configuration Keycloak...")
        kc = KeycloakClient(self.kc_url, "admin", self.admin_password)
        kc.auth()

        # Create realm and groups
        kc.create_realm("labomatics", display_name="labomatics")
        superadmin_gid = kc.create_group("labomatics", "superadmin")
        prof_gid = kc.create_group("labomatics", "prof")
        student_gid = kc.create_group("labomatics", "student")

        # Create roles
        kc.create_realm_role("labomatics", "admin", "Administrator", composite=True)
        kc.create_realm_role("labomatics", "teacher", "Teacher")
        kc.create_realm_role("labomatics", "student", "Student")

        try:
            kc.add_all_client_roles_to_role("labomatics", "admin")
        except RuntimeError as e:
            warning(f"Permissions admin (optionnel): {e}")

        kc.add_realm_role_to_group("labomatics", superadmin_gid, "admin")
        kc.add_realm_role_to_group("labomatics", prof_gid, "teacher")
        kc.add_realm_role_to_group("labomatics", student_gid, "student")

        try:
            kc.set_default_group("labomatics", student_gid)
        except RuntimeError as e:
            warning(f"Groupe par défaut (optionnel): {e}")

        # Create admin user
        username = f"{admin_first_name.lower()}.{admin_last_name.lower()}".replace(
            " ", "-"
        )
        user_password = secrets.token_urlsafe(16)
        user_id = kc.create_user(
            "labomatics",
            username,
            first_name=admin_first_name,
            last_name=admin_last_name,
            email=admin_email,
        )
        kc.set_user_password("labomatics", user_id, user_password, temporary=True)
        kc.add_user_to_group("labomatics", user_id, superadmin_gid)

        # Create Proxmox client with FQDNs as redirect URIs
        node_fqdns = self.state.get("node_dns_entries") or {}
        redirect_uris = [f"https://{fqdn}/" for fqdn in node_fqdns.keys()]
        # Get actual cluster name from Proxmox
        cluster_name = self.pve.get_cluster_name() if self.pve else "proxmox"
        client_id = f"proxmox-{cluster_name.lower()}"
        client_secret = kc.create_client(
            "labomatics",
            client_id=client_id,
            name="Proxmox",
            redirect_uris=redirect_uris,
        )

        self.state.set("labomatics_user_password", user_password)
        self.state.set("proxmox_client_id", client_id)
        self.state.set("proxmox_oidc_secret", client_secret)
        self.state.set("admin_first_name", admin_first_name)
        self.state.set("admin_last_name", admin_last_name)

        success("Keycloak configuré")

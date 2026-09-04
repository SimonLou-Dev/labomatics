"""Keycloak setup."""

import secrets

from ...utils.keycloak import KeycloakClient
from ...utils.verify import ServiceVerifier
from ...utils.state import InstallState
from ...utils.theme import info, success, warning


class KeycloakSetup:
    """Configuration Keycloak."""

    def __init__(
        self,
        domain: str,
        admin_password: str,
        state: InstallState,
        pve=None,
        ldap_base_dn: str = None,
        ldap_secrets: dict = None,
    ):
        """Initialiser."""
        self.domain = domain
        self.admin_password = admin_password
        self.state = state
        self.pve = pve
        self.kc_url = f"https://keycloak.{domain}"
        self.ldap_base_dn = ldap_base_dn
        self.ldap_secrets = ldap_secrets or {}

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
        kc.create_realm_role(
            "labomatics",
            "manage_user",
            "Gestion des utilisateurs (CRUD compte, changement de groupe)",
        )
        kc.create_realm_role(
            "labomatics",
            "manage_cluster",
            "Gestion des clusters Proxmox (admin des plages IP/VXLAN, credentials)",
        )

        try:
            kc.add_all_client_roles_to_role("labomatics", "admin")
        except RuntimeError as e:
            warning(f"Permissions admin (optionnel): {e}")

        kc.add_realm_role_to_group("labomatics", superadmin_gid, "admin")
        kc.add_realm_role_to_group("labomatics", superadmin_gid, "manage_user")
        kc.add_realm_role_to_group("labomatics", superadmin_gid, "manage_cluster")
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
        existing_user = kc.get_user_by_username("labomatics", username)
        if existing_user:
            info(f"User {username} existe déjà, credentials conservés")
            user_id = existing_user["id"]
            user_password = None
        else:
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

        # Create labomatics-admin service account (non-temporary password)
        existing_admin_svc = kc.get_user_by_username("labomatics", "labomatics-admin")
        if existing_admin_svc:
            info("User labomatics-admin existe déjà, credentials conservés")
            admin_svc_id = existing_admin_svc["id"]
            admin_svc_password = None
        else:
            admin_svc_password = secrets.token_urlsafe(16)
            admin_svc_id = kc.create_user(
                "labomatics",
                "labomatics-admin",
                first_name="Labomatics",
                last_name="Admin",
                email=f"admin@labomatics.{self.domain}",
            )
            kc.set_user_password(
                "labomatics", admin_svc_id, admin_svc_password, temporary=False
            )
        # Assign realm-management client roles (no group)
        for role_name in (
            "manage-users",
            "view-users",
            "manage-clients",
            "view-clients",
        ):
            try:
                kc.assign_client_role_to_user(
                    "labomatics", admin_svc_id, "realm-management", role_name
                )
            except RuntimeError as e:
                warning(f"Failed to assign role {role_name} to labomatics-admin: {e}")

        # Create labomatics (web frontend) client - confidential with authorization
        labomatics_redirect_uris = [
            f"https://api.{self.domain}/v1/auth/callback",
            "http://localhost:5173/#/",
            "http://localhost:8001/#/",
        ]
        labomatics_client_secret = kc.create_client(
            "labomatics",
            client_id="labomatics",
            name="Labomatics Web",
            redirect_uris=labomatics_redirect_uris,
            public_client=False,
            enable_auth=True,
        )
        self.state.set("labomatics_client_id", "labomatics")
        self.state.set("labomatics_client_secret", labomatics_client_secret)
        # Create client role manage-user
        kc.create_client_role(
            "labomatics",
            "labomatics",
            "manage-user",
            "Gestion des utilisateurs (CRUD compte, changement de groupe)",
        )

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
        self.state.set("labomatics_admin_username", "labomatics-admin")
        self.state.set("labomatics_admin_password", admin_svc_password)
        self.state.set("proxmox_client_id", client_id)
        self.state.set("proxmox_oidc_secret", client_secret)
        self.state.set("admin_first_name", admin_first_name)
        self.state.set("admin_last_name", admin_last_name)

        if user_password is None:
            warning(
                f"L'utilisateur {username} existe déjà. Utilisez ses credentials existants."
            )
        if admin_svc_password is None:
            warning(
                "Le compte labomatics-admin existe déjà. Utilisez ses credentials existants."
            )

        # Configure LDAP federation if secrets provided
        if self.ldap_base_dn and self.ldap_secrets:
            self._setup_ldap_federation(kc, self.ldap_base_dn, self.ldap_secrets)

        success("Keycloak configuré")

    def _setup_ldap_federation(self, kc, base_dn: str, secrets: dict) -> None:
        """Configurer la fédération LDAP et le mapper de groupes."""
        info("Configuration fédération LDAP...")
        ldap_bind_dn = f"cn=keycloak-bind,ou=svcaccounts,{base_dn}"
        ldap_component_id = kc.create_ldap_federation(
            "labomatics",
            base_dn,
            ldap_bind_dn,
            secrets.get("ldap_keycloak_bind_password", ""),
        )
        success(f"  LDAP federation créée (id={ldap_component_id})")

        info("Configuration Group LDAP Mapper...")
        kc.create_group_ldap_mapper("labomatics", ldap_component_id, base_dn)
        success("  Group LDAP Mapper créé")

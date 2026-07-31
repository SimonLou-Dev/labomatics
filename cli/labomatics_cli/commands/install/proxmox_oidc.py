"""Proxmox OIDC setup."""

from ...utils.proxmox import ProxmoxClient
from ...utils.state import InstallState
from ...utils.theme import info, success, error


class ProxmoxOIDCSetup:
    """Configuration Proxmox OIDC."""

    def __init__(self, pve: ProxmoxClient, domain: str, state: InstallState):
        """Initialiser."""
        self.pve = pve
        self.domain = domain
        self.state = state

    def setup(self, admin_first_name: str, admin_last_name: str, admin_email: str):
        """Configurer Proxmox OIDC."""
        try:
            info("Configuration Proxmox OIDC...")

            client_id = self.state.get("proxmox_client_id")
            client_secret = self.state.get("proxmox_oidc_secret")

            self.pve.configure_oidc_realm(
                realm_name="labomatics",
                issuer_url=f"https://keycloak.{self.domain}/realms/labomatics",
                client_id=client_id,
                client_key=client_secret,
                username_claim="preferred_username",
                default=True,
            )
            success("Proxmox OIDC configuré")

            info("Création user OIDC admin...")
            admin_username = (
                f"{admin_first_name.lower()}.{admin_last_name.lower()}".replace(
                    " ", "-"
                )
            )
            self.pve.create_oidc_user(admin_username, "labomatics", email=admin_email)

            info("Attribution Administrator...")
            self.pve.proxmox.access.acl.put(
                path="/",
                users=f"{admin_username}@labomatics",
                roles="Administrator",
            )
            success(f"User {admin_username} est Administrator")

        except Exception as e:
            error(f"Configuration Proxmox OIDC: {e}")
            raise

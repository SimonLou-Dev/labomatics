"""Tâche 9 : realm, groupes, rôles, comptes, clients et fédération LDAP de Keycloak."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.directory import DirectoryInfo
from labomatics_cli.installer.keycloak_api import REALM, KeycloakApi
from labomatics_cli.installer.ldap_federation import LdapFederation
from labomatics_cli.installer.tasks.base import InstallTask

PASSWORD_POLICY = (
    "length(16) and specialChars(2) and upperCase(2) and digits(2) "
    "and lowerCase(3) and passwordHistory(3) and notUsername"
)
GROUP_ROLES = {
    "superadmin": ("admin", "manage_user", "manage_cluster"),
    "prof": ("teacher",),
    "student": ("student",),
}
REALM_ROLES = (
    ("admin", "Administrator", True),
    ("teacher", "Teacher", False),
    ("student", "Student", False),
    (
        "manage_user",
        "Gestion des utilisateurs (CRUD compte, changement de groupe)",
        False,
    ),
    (
        "manage_cluster",
        "Gestion des clusters Proxmox (admin des plages IP/VXLAN, credentials)",
        False,
    ),
)
SERVICE_ACCOUNT = "labomatics-admin"
SERVICE_ROLES = ["manage-users", "view-users", "manage-clients", "view-clients"]
CLIENT_ID = "labomatics"


class KeycloakTask(InstallTask):
    """Configure le realm `labomatics` ; tout est créé ou mis à jour."""

    name = "keycloak"
    label = "Keycloak"

    def run(self, ctx: InstallContext) -> None:
        """Applique la configuration Keycloak puis enregistre le secret du client.

        Args:
            ctx: Contexte d'installation.
        """
        api = ctx.keycloak
        ctx.log("Attente de Keycloak")
        api.wait_ready()
        realm_id = api.ensure_realm(REALM, self._realm_settings(ctx))
        ctx.log("Realm labomatics configuré (politique de mots de passe, SMTP)", "ok")
        groups = self._roles_and_groups(api)
        self._accounts(ctx, api, groups)
        self._client(ctx, api)
        api.add_all_client_roles_to_role(REALM, "admin")
        info = DirectoryInfo(ctx.config, ctx.store.secrets)
        if info.enabled:
            self._federation(ctx, api, realm_id, info)

    def _realm_settings(self, ctx: InstallContext) -> dict:
        """Paramètres du realm : politique de mots de passe et SMTP.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Les champs de la représentation du realm à appliquer.
        """
        mail = ctx.config.mail
        settings: dict = {
            "displayName": "labomatics",
            "passwordPolicy": PASSWORD_POLICY,
            "smtpServer": {},
            "resetPasswordAllowed": False,
        }
        if mail is not None and mail.enabled:
            settings["resetPasswordAllowed"] = True
            settings["smtpServer"] = {
                "host": mail.smtp_host,
                "port": str(mail.smtp_port),
                "from": mail.from_email,
                "fromDisplayName": mail.from_name,
                "starttls": str(mail.smtp_starttls).lower(),
                "ssl": "false",
                "auth": str(bool(mail.smtp_user)).lower(),
                "user": mail.smtp_user,
                "password": mail.smtp_password,
            }
        return settings

    def _roles_and_groups(self, api: KeycloakApi) -> dict[str, str]:
        """Crée les rôles, les groupes et leurs associations.

        Args:
            api: Client Keycloak.

        Returns:
            Les identifiants des groupes par nom.
        """
        for name, description, composite in REALM_ROLES:
            api.ensure_realm_role(REALM, name, description, composite)
        groups = {name: api.ensure_group(REALM, name) for name in GROUP_ROLES}
        for name, roles in GROUP_ROLES.items():
            for role in roles:
                api.add_role_to_group(REALM, groups[name], role)
        api.set_default_group(REALM, groups["student"])
        return groups

    def _accounts(
        self, ctx: InstallContext, api: KeycloakApi, groups: dict[str, str]
    ) -> None:
        """Crée l'administrateur et le compte de service du backend.

        Les mots de passe ne sont posés qu'à la création, pour ne pas écraser un changement.

        Args:
            ctx: Contexte d'installation.
            api: Client Keycloak.
            groups: Identifiants des groupes par nom.
        """
        assert ctx.config.admin is not None and ctx.config.vm is not None
        admin, secrets = ctx.config.admin, ctx.store.secrets
        user_id, _ = api.ensure_user(
            REALM,
            admin.username,
            {
                "firstName": admin.first_name,
                "lastName": admin.last_name,
                "email": admin.email,
                "emailVerified": True,
            },
        )
        if not api.has_password(REALM, user_id):
            api.set_password(REALM, user_id, secrets.admin_temp_password or "", True)
        api.add_user_to_group(REALM, user_id, groups["superadmin"])
        ctx.store.set_data("admin_username", admin.username)
        ctx.log(f"Administrateur {admin.username} prêt", "ok")

        service_id, _ = api.ensure_user(
            REALM,
            SERVICE_ACCOUNT,
            {
                "firstName": "Labomatics",
                "lastName": "Admin",
                "email": f"admin@labomatics.{ctx.config.vm.domain}",
                "emailVerified": True,
            },
        )
        if not api.has_password(REALM, service_id):
            api.set_password(
                REALM, service_id, secrets.labomatics_admin_password or "", False
            )
        api.assign_client_roles(REALM, service_id, "realm-management", SERVICE_ROLES)
        ctx.log(f"Compte de service {SERVICE_ACCOUNT} prêt", "ok")

    def _client(self, ctx: InstallContext, api: KeycloakApi) -> str:
        """Crée le client web `labomatics` et conserve son secret.

        Args:
            ctx: Contexte d'installation.
            api: Client Keycloak.

        Returns:
            L'identifiant interne du client.
        """
        assert ctx.config.vm is not None
        domain = ctx.config.vm.domain
        client_uuid = api.ensure_client(
            REALM,
            CLIENT_ID,
            {
                "name": "Labomatics Web",
                "redirectUris": [
                    f"https://labomatics.{domain}/*",
                    f"https://api.labomatics.{domain}/v1/auth/callback",
                ],
                "webOrigins": [f"https://labomatics.{domain}"],
                "standardFlowEnabled": True,
            },
        )
        api.ensure_client_role(
            REALM,
            client_uuid,
            "manage-user",
            "Gestion des utilisateurs (CRUD compte, changement de groupe)",
        )
        ctx.store.save_secret(
            "keycloak_client_secret", api.client_secret(REALM, client_uuid)
        )
        ctx.log("Client labomatics configuré", "ok")
        return client_uuid

    def _federation(
        self, ctx: InstallContext, api: KeycloakApi, realm_id: str, info: DirectoryInfo
    ) -> None:
        """Crée la fédération LDAP et ses mappers.

        Args:
            ctx: Contexte d'installation.
            api: Client Keycloak.
            realm_id: Identifiant interne du realm.
            info: Paramètres de l'annuaire.
        """
        federation = LdapFederation(info)
        provider_id = api.ensure_component(REALM, federation.provider(realm_id))
        for mapper in federation.mappers(provider_id):
            api.ensure_component(REALM, mapper)
        kind = "local" if info.local else "externe"
        ctx.log(f"Fédération LDAP {kind} configurée ({info.base_dn})", "ok")

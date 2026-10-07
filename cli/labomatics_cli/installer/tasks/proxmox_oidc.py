"""Tâche 10 : client Keycloak de Proxmox, realm OIDC et administrateur Proxmox."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.keycloak_api import REALM
from labomatics_cli.installer.tasks.base import InstallTask

REDIRECT_PATTERNS = (
    "https://{0}/*",
    "https://{0}:8006/*",
    "https://{0}",
    "https://{0}:8006",
)


class ProxmoxOidcTask(InstallTask):
    """Branche l'interface Proxmox sur Keycloak et donne le rôle Administrator à l'admin."""

    name = "proxmox_oidc"
    label = "Client Proxmox"

    def _hosts(self, ctx: InstallContext) -> list[str]:
        """Noms (ou à défaut IP) sous lesquels on atteint les nœuds.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Les FQDN relevés à l'étape DNS, sinon les IP des nœuds.
        """
        entries = ctx.store.get_data("node_dns_entries") or {}
        return list(entries) or [n.ip for n in ctx.proxmox.nodes() if n.ip]

    def run(self, ctx: InstallContext) -> None:
        """Crée le client Keycloak, le realm OIDC Proxmox et l'utilisateur administrateur.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.proxmox is not None and ctx.config.admin is not None
        assert ctx.config.vm is not None
        api, proxmox = ctx.keycloak, ctx.proxmox
        client_id = f"proxmox-{ctx.config.proxmox.cluster_name.lower()}"
        redirects = [p.format(h) for h in self._hosts(ctx) for p in REDIRECT_PATTERNS]
        client_uuid = api.ensure_client(
            REALM,
            client_id,
            {"name": "Proxmox", "redirectUris": redirects, "standardFlowEnabled": True},
        )
        ctx.log(f"Client Keycloak {client_id} configuré", "ok")

        issuer = f"https://keycloak.{ctx.config.vm.domain}/realms/{REALM}"
        created = proxmox.configure_oidc_realm(
            REALM, issuer, client_id, api.client_secret(REALM, client_uuid)
        )
        ctx.log(f"Realm OIDC Proxmox {'créé' if created else 'mis à jour'}", "ok")

        admin = ctx.config.admin
        userid = f"{admin.username}@{REALM}"
        if not proxmox.user_exists(userid):
            proxmox.create_user(userid, email=admin.email)
        proxmox.grant("/", userid, "Administrator")
        ctx.log(f"{userid} est Administrator Proxmox", "ok")

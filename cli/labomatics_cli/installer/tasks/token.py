"""Tâche 1 : utilisateur et jeton d'API Labomatics sur Proxmox."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask

USER_ID = "labomatics@pve"
TOKEN_NAME = "labomatics"


class TokenTask(InstallTask):
    """Crée `labomatics@pve`, son jeton sans séparation de privilèges et l'ACL Administrator."""

    name = "token"
    label = "Token Labomatics"

    def run(self, ctx: InstallContext) -> None:
        """Crée ou répare l'utilisateur, l'ACL et le jeton.

        Un jeton existant dont le secret n'est plus connu localement est recréé.

        Args:
            ctx: Contexte d'installation.
        """
        api = ctx.proxmox
        if not api.user_exists(USER_ID):
            api.create_user(USER_ID, "Utilisateur Labomatics")
            ctx.log(f"Utilisateur {USER_ID} créé", "ok")
        api.grant("/", USER_ID, "Administrator")
        known = bool(ctx.store.secrets.labomatics_token_secret)
        if api.token_exists(USER_ID, TOKEN_NAME):
            if known:
                ctx.log("Jeton existant, secret déjà connu", "ok")
                return
            ctx.log("Jeton existant au secret perdu : recréation", "warn")
            api.delete_token(USER_ID, TOKEN_NAME)
        ctx.store.save_secret(
            "labomatics_token_secret", api.create_token(USER_ID, TOKEN_NAME)
        )
        ctx.store.set_data("token_id", f"{USER_ID}!{TOKEN_NAME}")
        ctx.log("Jeton créé", "ok")

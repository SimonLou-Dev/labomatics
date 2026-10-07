"""Tâche 11 : jeton du backend, clusterconfig.yaml, backend.env et redémarrage."""

from __future__ import annotations

from labomatics_cli.installer.clusterconfig import ClusterConfigBuilder
from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.stack import STACK_ROOT, StackFiles
from labomatics_cli.installer.tasks.base import InstallTask
from labomatics_cli.installer.tasks.token import USER_ID

BACKEND_TOKEN = "backend"
RESTART = f"cd {STACK_ROOT} && sudo docker compose up -d --force-recreate api worker"


class BackendTask(InstallTask):
    """Prépare la configuration du backend puis recrée l'API et les workers."""

    name = "backend"
    label = "YAML d'init du backend"

    def run(self, ctx: InstallContext) -> None:
        """Crée le jeton, dépose le YAML et le `backend.env`, recrée `api` et `worker`.

        Les conteneurs sont recréés (et non redémarrés) : `restart` ne relit pas `env_file`.

        Args:
            ctx: Contexte d'installation.
        """
        secret = self._token(ctx)
        ssh = ctx.vm_ssh
        builder = ClusterConfigBuilder(ctx.config)
        ssh.put_text(
            f"{STACK_ROOT}/clusterconfig.yaml",
            builder.render(f"{USER_ID}!{BACKEND_TOKEN}", secret),
            0o600,
        )
        ctx.log("clusterconfig.yaml déposé", "ok")

        files = StackFiles(ctx.config, ctx.store.secrets, ctx.templates)
        env = next(f for f in files.selected() if f.target == "backend.env")
        ssh.put_text(f"{STACK_ROOT}/{env.target}", files.render(env), env.mode)
        ctx.log("backend.env réécrit avec le secret Keycloak", "ok")

        ssh.run(RESTART, timeout=600)
        ctx.log("API et workers recréés", "ok")

    def _token(self, ctx: InstallContext) -> str:
        """Garantit le jeton `labomatics@pve!backend` et renvoie son secret.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Le secret du jeton ; un jeton au secret perdu est recréé.
        """
        api = ctx.proxmox
        known = ctx.store.secrets.backend_token_secret
        if api.token_exists(USER_ID, BACKEND_TOKEN):
            if known:
                return known
            ctx.log("Jeton backend au secret perdu : recréation", "warn")
            api.delete_token(USER_ID, BACKEND_TOKEN)
        secret = api.create_token(USER_ID, BACKEND_TOKEN)
        ctx.store.save_secret("backend_token_secret", secret)
        ctx.log("Jeton backend créé", "ok")
        return secret

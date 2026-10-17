"""Tâche 11 : jeton du backend, clusterconfig.yaml, backend.env et démarrage de l'app."""

from __future__ import annotations

from labomatics_cli.installer.clusterconfig import ClusterConfigBuilder
from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.stack import APP_SERVICES, STACK_ROOT, StackFiles
from labomatics_cli.installer.tasks.base import InstallTask
from labomatics_cli.installer.tasks.token import USER_ID

BACKEND_TOKEN = "backend"
PVE_ROOT_CA = "/etc/pve/pve-root-ca.pem"
START_APP = (
    f"cd {STACK_ROOT} && sudo docker compose up -d --force-recreate "
    + " ".join(APP_SERVICES)
)


class BackendTask(InstallTask):
    """Prépare la configuration du backend puis démarre l'API, le worker et le frontend."""

    name = "backend"
    label = "YAML d'init du backend"

    def run(self, ctx: InstallContext) -> None:
        """Crée le jeton, dépose le YAML et le `backend.env`, puis lance l'application.

        Premier démarrage de `api`, `worker` et `frontend` : ils ont besoin du realm,
        du secret du client Keycloak et du clusterconfig.yaml. Ils sont recréés (et non
        redémarrés) aux passages suivants : `restart` ne relit pas `env_file`.

        Args:
            ctx: Contexte d'installation.
        """
        secret = self._token(ctx)
        ssh = ctx.vm_ssh
        ca_cert = self._proxmox_ca(ctx)
        builder = ClusterConfigBuilder(ctx.config)
        ssh.put_text(
            f"{STACK_ROOT}/clusterconfig.yaml",
            builder.render(f"{USER_ID}!{BACKEND_TOKEN}", secret, ca_cert),
            0o600,
        )
        ctx.log("clusterconfig.yaml déposé", "ok")

        files = StackFiles(ctx.config, ctx.store.secrets, ctx.templates)
        env = next(f for f in files.selected() if f.target == "backend.env")
        ssh.put_text(f"{STACK_ROOT}/{env.target}", files.render(env), env.mode)
        ctx.log("backend.env réécrit avec le secret Keycloak", "ok")

        ctx.log(
            "Démarrage de l'API, du worker et du frontend (téléchargement des images)"
        )
        ssh.run(START_APP, timeout=1800)
        ctx.log("API, worker et frontend démarrés", "ok")

    def _proxmox_ca(self, ctx: InstallContext) -> str | None:
        """Récupère la CA du cluster Proxmox pour que le backend vérifie son TLS.

        `/etc/pve/` est partagé entre tous les nœuds d'un même cluster (pmxcfs) :
        un seul nœud suffit à obtenir la CA, commune à tout le cluster.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Le PEM de la CA, ou `None` si elle n'a pas pu être lue (log en warning).
        """
        node = next(iter(ctx.config.nodes), None)
        if node is None:
            ctx.log("Aucun nœud Proxmox configuré : CA non récupérée", "warn")
            return None
        result = ctx.node_ssh(node).run(f"cat {PVE_ROOT_CA}", check=False)
        if not result.ok or not result.stdout.strip():
            ctx.log(
                f"CA Proxmox introuvable sur {node} : vérif TLS backend dégradée",
                "warn",
            )
            return None
        ctx.log("CA Proxmox récupérée", "ok")
        return result.stdout

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

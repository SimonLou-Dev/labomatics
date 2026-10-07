"""Tâche 7 : CA, certificats, fichiers de la stack et démarrage de l'infrastructure."""

from __future__ import annotations

import posixpath

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.stack import APP_SERVICES, STACK_ROOT, StackFiles
from labomatics_cli.installer.tasks.base import InstallTask

PREPARE_SCRIPT = f"""set -e
sudo mkdir -p {STACK_ROOT}/certs
sudo chown -R labomatics:labomatics {STACK_ROOT}
sudo chmod 755 {STACK_ROOT}
"""
APP_PATTERN = "|".join(APP_SERVICES)
UP_SCRIPT = (
    f"cd {STACK_ROOT} && sudo docker compose up -d --remove-orphans "
    f"$(sudo docker compose config --services | grep -vxE '{APP_PATTERN}')"
)
CERTS_TMP = "/tmp/labomatics-generate-certs.sh"
WAIT_TMP = "/tmp/labomatics-wait-ready.sh"
PLACEHOLDER_CLUSTERCONFIG = "clusters: []\n"


class StackTask(InstallTask):
    """Génère la CA et les certificats, dépose les fichiers et démarre l'infrastructure.

    L'API, le worker et le frontend attendent la tâche backend : il leur faut le
    realm Keycloak, le secret du client et le clusterconfig.yaml.
    """

    name = "stack"
    label = "CA, templates et docker up"

    def run(self, ctx: InstallContext) -> None:
        """Prépare le dossier, génère les certificats, dépose les fichiers et démarre l'infra.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        ssh = ctx.vm_ssh
        files = StackFiles(ctx.config, ctx.store.secrets, ctx.templates)
        ssh.run(PREPARE_SCRIPT)
        domain = ctx.config.vm.domain

        ssh.put_text(
            CERTS_TMP,
            ctx.templates.render("stack/init/generate-certs.sh.j2", domain=domain),
        )
        for line in ssh.run(f"bash {CERTS_TMP}").stdout.strip().splitlines():
            ctx.log(line, "ok")

        self._write_files(ctx, files)
        ctx.log("Démarrage de l'infrastructure (téléchargement des images)")
        ssh.run(UP_SCRIPT, timeout=1800)
        ctx.log("Postgres, Redis, Keycloak et Traefik démarrés", "ok")

        ssh.put_text(
            WAIT_TMP, ctx.templates.render("stack/init/wait-ready.sh.j2", domain=domain)
        )
        for line in ssh.run(f"bash {WAIT_TMP}").stdout.strip().splitlines():
            ctx.log(line, "ok")

    def _write_files(self, ctx: InstallContext, files: StackFiles) -> None:
        """Dépose les fichiers rendus et un clusterconfig vide s'il n'existe pas encore.

        Args:
            ctx: Contexte d'installation.
            files: Fichiers de la stack.
        """
        ssh = ctx.vm_ssh
        selected = files.selected()
        folders = sorted({posixpath.dirname(f.target) for f in selected} - {""})
        if folders:
            ssh.run("mkdir -p " + " ".join(f"{STACK_ROOT}/{d}" for d in folders))
        for item in selected:
            ssh.put_text(f"{STACK_ROOT}/{item.target}", files.render(item), item.mode)
        ssh.run(
            f"test -e {STACK_ROOT}/clusterconfig.yaml || "
            f"echo 'clusters: []' > {STACK_ROOT}/clusterconfig.yaml"
        )
        ctx.log(f"{len(selected)} fichiers déposés dans {STACK_ROOT}", "ok")

"""Tâche 7 : CA, certificats, fichiers de la stack et `docker compose up`."""

from __future__ import annotations

import posixpath

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.stack import STACK_ROOT, StackFiles
from labomatics_cli.installer.tasks.base import InstallTask

PREPARE_SCRIPT = f"""set -e
sudo mkdir -p {STACK_ROOT}/certs
sudo chown -R labomatics:labomatics {STACK_ROOT}
sudo chmod 755 {STACK_ROOT}
"""
UP_SCRIPT = f"cd {STACK_ROOT} && sudo docker compose up -d --remove-orphans"
CERTS_TMP = "/tmp/labomatics-generate-certs.sh"
WAIT_TMP = "/tmp/labomatics-wait-ready.sh"
PLACEHOLDER_CLUSTERCONFIG = "clusters: []\n"


class StackTask(InstallTask):
    """Génère la CA et les certificats, dépose les fichiers de la stack et la démarre."""

    name = "stack"
    label = "CA, templates et docker up"

    def run(self, ctx: InstallContext) -> None:
        """Prépare le dossier, génère les certificats, dépose les fichiers et démarre.

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
        ctx.log("Démarrage de la stack (téléchargement des images)")
        ssh.run(UP_SCRIPT, timeout=1800)
        ctx.log("Stack démarrée", "ok")

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

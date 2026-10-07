"""Tâche 4 : Docker sur la VM."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask

INSTALL_SCRIPT = """set -e
sudo dnf config-manager addrepo --overwrite --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker labomatics
docker --version
"""


class DockerTask(InstallTask):
    """Installe Docker Engine et le plugin compose sur la VM Fedora."""

    name = "docker"
    label = "Docker"
    skip_reason = "déjà installé"

    def is_needed(self, ctx: InstallContext) -> bool:
        """Vérifie si Docker est déjà installé.

        Args:
            ctx: Contexte d'installation.

        Returns:
            False si `docker --version` répond.
        """
        return not ctx.vm_ssh.run("docker --version", check=False).ok

    def run(self, ctx: InstallContext) -> None:
        """Installe Docker.

        Args:
            ctx: Contexte d'installation.
        """
        ctx.log("Installation de Docker")
        result = ctx.vm_ssh.run(INSTALL_SCRIPT)
        ctx.log(result.stdout.strip().splitlines()[-1], "ok")

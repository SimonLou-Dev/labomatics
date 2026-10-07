"""Tâche 8 : propagation de la CA Labomatics sur les nœuds Proxmox."""

from __future__ import annotations

import hashlib

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask

CA_SOURCE = "/etc/labomatics/certs/ca.crt"
CA_TARGET = "/usr/local/share/ca-certificates/labomatics.crt"


class CaPropagationTask(InstallTask):
    """Installe la CA dans le magasin de confiance de chaque nœud, si elle a changé."""

    name = "ca_propagation"
    label = "Propagation des CA"

    def run(self, ctx: InstallContext) -> None:
        """Copie la CA et lance `update-ca-certificates` sur chaque nœud.

        Args:
            ctx: Contexte d'installation.
        """
        ca = ctx.vm_ssh.run(f"cat {CA_SOURCE}").stdout
        fingerprint = hashlib.sha256(ca.encode()).hexdigest()
        for node in ctx.config.nodes:
            ssh = ctx.node_ssh(node)
            current = ssh.run(f"sha256sum {CA_TARGET}", check=False)
            if current.ok and current.stdout.split()[:1] == [fingerprint]:
                ctx.log(f"CA déjà en place sur {node}", "ok")
                continue
            ssh.run("mkdir -p /usr/local/share/ca-certificates")
            ssh.put_text(CA_TARGET, ca)
            ssh.run("update-ca-certificates")
            ctx.log(f"CA installée sur {node}", "ok")

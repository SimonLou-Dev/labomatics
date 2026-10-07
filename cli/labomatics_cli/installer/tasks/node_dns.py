"""Tâche 6 : DNS des nœuds Proxmox."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask


class NodeDnsTask(InstallTask):
    """Pointe le DNS de chaque nœud vers la VM, via l'API Proxmox."""

    name = "node_dns"
    label = "DNS des nœuds Proxmox"

    def run(self, ctx: InstallContext) -> None:
        """Met à jour les nœuds dont le DNS diffère.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        vm = ctx.config.vm
        for node in ctx.proxmox.nodes():
            current = ctx.proxmox.node_dns(node.name)
            if current.get("dns1") == vm.vm_ip and current.get("search") == vm.domain:
                ctx.log(f"DNS de {node.name} déjà à jour", "ok")
                continue
            ctx.proxmox.set_node_dns(node.name, vm.vm_ip, vm.domain)
            ctx.log(f"DNS de {node.name} -> {vm.vm_ip}", "ok")

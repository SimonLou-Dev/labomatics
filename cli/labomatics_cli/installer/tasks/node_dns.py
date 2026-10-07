"""Tâche 6 : DNS des nœuds Proxmox."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask


class NodeDnsTask(InstallTask):
    """Pointe le DNS de chaque nœud vers la VM, avec les DNS amont en secours, via l'API Proxmox.

    Les DNS amont restent configurés pour que les nœuds résolvent encore les
    noms quand la VM est arrêtée ou pas encore créée (réinstallation).
    """

    name = "node_dns"
    label = "DNS des nœuds Proxmox"

    def run(self, ctx: InstallContext) -> None:
        """Met à jour les nœuds dont le DNS diffère.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        vm = ctx.config.vm
        servers = [vm.vm_ip, *[ip for ip in vm.dns_upstream if ip != vm.vm_ip]][:3]
        wanted = {f"dns{i}": ip for i, ip in enumerate(servers, start=1)}
        for node in ctx.proxmox.nodes():
            current = ctx.proxmox.node_dns(node.name)
            same = all(current.get(k) == v for k, v in wanted.items())
            if same and current.get("search") == vm.domain:
                ctx.log(f"DNS de {node.name} déjà à jour", "ok")
                continue
            ctx.proxmox.set_node_dns(node.name, servers, vm.domain)
            ctx.log(f"DNS de {node.name} -> {', '.join(servers)}", "ok")

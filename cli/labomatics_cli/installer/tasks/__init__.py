"""Tâches d'installation, dans l'ordre d'exécution."""

from __future__ import annotations

from labomatics_cli.installer.tasks.base import InstallTask, PendingTask
from labomatics_cli.installer.tasks.dns import DnsTask
from labomatics_cli.installer.tasks.docker import DockerTask
from labomatics_cli.installer.tasks.node_dns import NodeDnsTask
from labomatics_cli.installer.tasks.sdn import SdnTask
from labomatics_cli.installer.tasks.token import TokenTask
from labomatics_cli.installer.tasks.vm import VmTask

__all__ = ["InstallTask", "PendingTask", "build_tasks"]


def build_tasks() -> list[InstallTask]:
    """Construit la liste des 13 tâches (les tâches 7 à 13 sont provisoires).

    Returns:
        Les tâches dans l'ordre d'exécution.
    """
    return [
        TokenTask(),
        SdnTask(),
        VmTask(),
        DockerTask(),
        DnsTask(),
        NodeDnsTask(),
        PendingTask("stack", "CA, templates et docker up"),
        PendingTask("ca_propagation", "Propagation des CA"),
        PendingTask("keycloak", "Keycloak"),
        PendingTask("proxmox_oidc", "Client Proxmox"),
        PendingTask("backend", "YAML d'init du backend"),
        PendingTask("agent", "Agent"),
        PendingTask("health", "Contrôle de santé"),
    ]

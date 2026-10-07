"""Tâches d'installation, dans l'ordre d'exécution."""

from __future__ import annotations

from labomatics_cli.installer.tasks.agent import AgentTask
from labomatics_cli.installer.tasks.backend import BackendTask
from labomatics_cli.installer.tasks.base import InstallTask
from labomatics_cli.installer.tasks.ca_propagation import CaPropagationTask
from labomatics_cli.installer.tasks.dns import DnsTask
from labomatics_cli.installer.tasks.docker import DockerTask
from labomatics_cli.installer.tasks.health import HealthTask
from labomatics_cli.installer.tasks.keycloak import KeycloakTask
from labomatics_cli.installer.tasks.node_dns import NodeDnsTask
from labomatics_cli.installer.tasks.proxmox_oidc import ProxmoxOidcTask
from labomatics_cli.installer.tasks.sdn import SdnTask
from labomatics_cli.installer.tasks.stack import StackTask
from labomatics_cli.installer.tasks.token import TokenTask
from labomatics_cli.installer.tasks.vm import VmTask

__all__ = ["InstallTask", "build_tasks"]


def build_tasks() -> list[InstallTask]:
    """Construit la liste des 13 tâches.

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
        StackTask(),
        CaPropagationTask(),
        KeycloakTask(),
        ProxmoxOidcTask(),
        BackendTask(),
        AgentTask(),
        HealthTask(),
    ]

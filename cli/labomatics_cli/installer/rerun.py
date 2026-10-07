"""Tâches à rejouer selon les champs modifiés en mode édition."""

from __future__ import annotations

from typing import Any

from labomatics_cli.models.install_config import InstallConfig

DOMAIN_TASKS = (
    "dns",
    "node_dns",
    "stack",
    "ca_propagation",
    "keycloak",
    "proxmox_oidc",
    "backend",
)

RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vm.domain", DOMAIN_TASKS),
    ("vm.dns_upstream", ("dns",)),
    ("proxy.", ("stack",)),
    ("mail.", ("stack", "keycloak", "backend")),
    ("auth.", ("stack", "keycloak")),
    ("ldap.", ("stack", "keycloak")),
    ("wan.", ("sdn", "backend")),
    ("vxlan.", ("sdn", "backend")),
    ("admin.", ("keycloak", "proxmox_oidc")),
    ("nodes.", ("ca_propagation",)),
    ("proxmox.url", ("backend",)),
)


class RerunPlanner:
    """Compare deux configurations et liste les tâches à rejouer."""

    def __init__(self, old: InstallConfig, new: InstallConfig) -> None:
        """Initialise le planificateur.

        Args:
            old: Configuration avant le wizard.
            new: Configuration après le wizard.
        """
        self.old = old
        self.new = new

    def changed_keys(self) -> set[str]:
        """Clés plates dont la valeur diffère (ajoutées, modifiées ou retirées).

        Returns:
            Les clés « section.champ » modifiées.
        """
        before: dict[str, Any] = self.old.to_flat()
        after: dict[str, Any] = self.new.to_flat()
        return {
            k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
        }

    def plan(self) -> set[str]:
        """Tâches à rejouer pour appliquer les modifications.

        Returns:
            Les noms de tâches ; vide si rien n'a changé d'utile.
        """
        tasks: set[str] = set()
        for key in self.changed_keys():
            for prefix, names in RULES:
                if key.startswith(prefix):
                    tasks.update(names)
        return tasks

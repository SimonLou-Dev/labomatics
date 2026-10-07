"""Fichiers de la stack Docker déposés dans `/etc/labomatics` de la VM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from labomatics_cli.installer.directory import DirectoryInfo
from labomatics_cli.installer.secrets import InstallSecrets
from labomatics_cli.installer.templates import TemplateRenderer
from labomatics_cli.models.install_config import InstallConfig, MailSection

STACK_ROOT = "/etc/labomatics"


@dataclass(frozen=True)
class StackFile:
    """Un fichier rendu depuis un template et déposé sur la VM."""

    template: str
    target: str
    mode: int = 0o644
    when: Optional[Callable[[DirectoryInfo], bool]] = None

    def applies(self, info: DirectoryInfo) -> bool:
        """Indique si le fichier concerne cette configuration.

        Args:
            info: Paramètres de l'annuaire.

        Returns:
            True si le fichier est toujours déposé ou si sa condition est vraie.
        """
        return self.when is None or self.when(info)


STACK_FILES = (
    StackFile("stack/docker-compose.yml.j2", "docker-compose.yml", 0o600),
    StackFile("stack/init/init-databases.sh", "init-databases.sh"),
    StackFile("stack/init/init-backend.sh", "init-backend.sh"),
    StackFile("stack/env/backend.env.j2", "backend.env", 0o600),
    StackFile("stack/env/frontend.env.j2", "frontend.env"),
    StackFile("traefik/traefik.yml.j2", "traefik.yml"),
    StackFile("traefik/dynamic.yml.j2", "dynamic/dynamic.yml"),
    StackFile(
        "ldap/bootstrap.ldif.j2", "ldap/bootstrap.ldif", 0o644, lambda i: i.local
    ),
    StackFile("ldap/setup-acls.sh", "ldap/setup-acls.sh", 0o644, lambda i: i.local),
    StackFile(
        "radius/clients.conf.j2", "radius/clients.conf", 0o644, lambda i: i.radius
    ),
    StackFile(
        "radius/mods-ldap.j2", "radius/mods-enabled/ldap", 0o644, lambda i: i.radius
    ),
    StackFile(
        "radius/site-default", "radius/sites-enabled/default", 0o644, lambda i: i.radius
    ),
)


class StackFiles:
    """Rend les fichiers de la stack à partir de la configuration et des secrets."""

    def __init__(
        self,
        config: InstallConfig,
        secrets: InstallSecrets,
        templates: TemplateRenderer,
    ) -> None:
        """Initialise le rendu.

        Args:
            config: Réponses du wizard (page VM et suivantes renseignées).
            secrets: Secrets du cluster.
            templates: Moteur de templates.
        """
        assert config.vm is not None and config.wan is not None
        self.config = config
        self.secrets = secrets
        self.templates = templates
        self.directory = DirectoryInfo(config, secrets)

    def variables(self) -> dict[str, Any]:
        """Variables communes à tous les templates.

        Returns:
            Les variables Jinja : domaine, secrets, annuaire, mail, proxy…
        """
        assert self.config.vm is not None and self.config.wan is not None
        mail = self.config.mail
        proxy = self.config.proxy
        return {
            "domain": self.config.vm.domain,
            "timezone": self.config.vm.timezone,
            "wan_iface": self.config.wan.iface,
            "secrets": self.secrets,
            "base_dn": self.directory.base_dn,
            "local_ldap": self.directory.local,
            "radius": self.directory.radius,
            "mail": mail if mail is not None and mail.enabled else MailSection(),
            "trusted_hosts": proxy.trusted_hosts if proxy else [],
        }

    def selected(self) -> list[StackFile]:
        """Fichiers concernés par la configuration (LDAP et RADIUS conditionnels).

        Returns:
            Les fichiers à déposer.
        """
        return [f for f in STACK_FILES if f.applies(self.directory)]

    def render(self, file: StackFile) -> str:
        """Rend un fichier.

        Args:
            file: Fichier de la stack.

        Returns:
            Le contenu rendu.
        """
        return self.templates.render(file.template, **self.variables())

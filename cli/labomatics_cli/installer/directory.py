"""Annuaire LDAP de l'installation (local ou externe) et RADIUS."""

from __future__ import annotations

from labomatics_cli.installer.secrets import InstallSecrets
from labomatics_cli.models.install_config import (
    AuthSection,
    DirectoryMode,
    InstallConfig,
)

LOCAL_URL = "ldap://ldap:389"
LOCAL_BIND_RDN = "cn=keycloak-bind,ou=svcaccounts"


class DirectoryInfo:
    """Paramètres de l'annuaire choisi à la page « Authentification »."""

    def __init__(self, config: InstallConfig, secrets: InstallSecrets) -> None:
        """Initialise les paramètres.

        Args:
            config: Réponses du wizard.
            secrets: Secrets du cluster (mot de passe du compte de bind local).
        """
        self.config = config
        self.secrets = secrets
        self.auth = config.auth or AuthSection()

    @property
    def enabled(self) -> bool:
        """Indique si Keycloak est fédéré à un annuaire.

        Returns:
            True pour un annuaire local ou externe.
        """
        return self.auth.directory != DirectoryMode.none

    @property
    def local(self) -> bool:
        """Indique si l'annuaire OpenLDAP est installé dans la stack.

        Returns:
            True pour « LDAP local ».
        """
        return self.auth.directory == DirectoryMode.local

    @property
    def radius(self) -> bool:
        """Indique si FreeRADIUS est installé (possible avec le LDAP local seulement).

        Returns:
            True si l'annuaire est local et que RADIUS est demandé.
        """
        return self.local and self.auth.radius

    @property
    def base_dn(self) -> str:
        """DN de base de l'annuaire.

        Returns:
            Le DN saisi (externe) ou dérivé du domaine, « lab.fr » donnant « dc=lab,dc=fr ».
        """
        if self.auth.directory == DirectoryMode.external and self.config.ldap:
            return self.config.ldap.base_dn
        domain = self.config.vm.domain if self.config.vm else "local"
        return ",".join(f"dc={part}" for part in domain.split("."))

    @property
    def url(self) -> str:
        """URL de connexion de Keycloak à l'annuaire.

        Returns:
            L'URL interne du conteneur (local) ou celle saisie (externe).
        """
        if self.local or self.config.ldap is None:
            return LOCAL_URL
        return self.config.ldap.url

    @property
    def bind_dn(self) -> str:
        """DN du compte de bind de Keycloak.

        Returns:
            Le compte de service local ou celui saisi.
        """
        if self.local or self.config.ldap is None:
            return f"{LOCAL_BIND_RDN},{self.base_dn}"
        return self.config.ldap.bind_dn

    @property
    def bind_password(self) -> str:
        """Mot de passe du compte de bind de Keycloak.

        Returns:
            Le secret généré (local) ou celui saisi (externe).
        """
        if self.local or self.config.ldap is None:
            return self.secrets.ldap_keycloak_bind_password or ""
        return self.config.ldap.bind_password

    @property
    def starttls(self) -> bool:
        """Indique si StartTLS est demandé.

        Returns:
            True pour un annuaire externe avec StartTLS.
        """
        return bool(not self.local and self.config.ldap and self.config.ldap.starttls)

    @property
    def uuid_attr(self) -> str:
        """Attribut UUID des entrées.

        Returns:
            `entryUUID` en local, la valeur saisie en externe.
        """
        if self.local or self.config.ldap is None:
            return "entryUUID"
        return self.config.ldap.uuid_attr

    @property
    def periodic_sync(self) -> bool:
        """Indique si les changements sont synchronisés périodiquement.

        Returns:
            True si demandé pour un annuaire externe.
        """
        return bool(
            not self.local and self.config.ldap and self.config.ldap.periodic_sync
        )

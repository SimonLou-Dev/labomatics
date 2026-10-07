"""Contexte partagé par les tâches d'installation."""

from __future__ import annotations

from typing import Callable, Optional

from labomatics_cli.installer.keycloak_api import KeycloakApi
from labomatics_cli.installer.proxmox_api import ProxmoxApi
from labomatics_cli.installer.ssh import CliKey, SshError, SshSession
from labomatics_cli.installer.store import InstallStore
from labomatics_cli.installer.templates import TemplateRenderer
from labomatics_cli.models.install_config import InstallConfig
from labomatics_cli.tui import InstallReporter

VM_USER = "labomatics"
VM_SSH_RETRIES = 60
VM_SSH_DELAY = 5.0


class InstallContext:
    """Configuration, store, rapporteur et clients (créés à la demande) d'une installation."""

    def __init__(
        self,
        config: InstallConfig,
        store: InstallStore,
        ui: InstallReporter,
        *,
        api_factory: Callable[..., ProxmoxApi] = ProxmoxApi,
        ssh_factory: Callable[..., SshSession] = SshSession,
        keycloak_factory: Callable[..., KeycloakApi] = KeycloakApi,
        key: Optional[CliKey] = None,
    ) -> None:
        """Initialise le contexte.

        Args:
            config: Réponses du wizard.
            store: Store du cluster (secrets, tâches, données).
            ui: Rapporteur de l'écran d'installation.
            api_factory: Construit le client Proxmox (url, utilisateur, jeton, secret).
            ssh_factory: Construit une session SSH, remplaçable en test.
            keycloak_factory: Construit le client Keycloak (url, utilisateur, mot de passe, host).
            key: Clé SSH du CLI.
        """
        self.config = config
        self.store = store
        self.ui = ui
        self.key = key or CliKey()
        self.templates = TemplateRenderer()
        self._api_factory = api_factory
        self._ssh_factory = ssh_factory
        self._keycloak_factory = keycloak_factory
        self._keycloak: Optional[KeycloakApi] = None
        self._proxmox: Optional[ProxmoxApi] = None
        self._vm_ssh: Optional[SshSession] = None
        self._sessions: list[SshSession] = []

    def log(self, message: str, level: str = "info") -> None:
        """Ajoute une ligne au journal d'installation.

        Args:
            message: Texte de la ligne.
            level: Niveau : info, ok, warn ou error.
        """
        self.ui.log(message, level)

    @property
    def proxmox(self) -> ProxmoxApi:
        """Client Proxmox du cluster, créé au premier accès.

        Returns:
            Le client connecté avec le jeton saisi dans le wizard.

        Raises:
            RuntimeError: Si la page Proxmox n'est pas renseignée.
        """
        if self._proxmox is None:
            section = self.config.proxmox
            if section is None:
                raise RuntimeError("Configuration Proxmox absente")
            self._proxmox = self._api_factory(
                section.url, section.user, section.token_id, section.token_secret
            )
        return self._proxmox

    @property
    def vm_ssh(self) -> SshSession:
        """Session SSH sur la VM Labomatics (clé du CLI), ouverte au premier accès.

        Returns:
            La session connectée.

        Raises:
            SshError: Si la VM reste injoignable.
        """
        if self._vm_ssh is None:
            vm = self.config.vm
            if vm is None:
                raise RuntimeError("Configuration de la VM absente")
            session = self._ssh_factory(
                vm.vm_ip,
                VM_USER,
                key_path=self.key.ensure(),
                retries=VM_SSH_RETRIES,
                delay=VM_SSH_DELAY,
            )
            session.connect()
            self._vm_ssh = session
            self._sessions.append(session)
        return self._vm_ssh

    @property
    def keycloak(self) -> KeycloakApi:
        """Client Keycloak (compte `admin` du realm master), créé au premier accès.

        L'API est jointe par l'IP de la VM avec l'en-tête `Host` du nom Keycloak :
        le PC d'administration n'a pas forcément le DNS du domaine.

        Returns:
            Le client, authentifié à la première requête.

        Raises:
            RuntimeError: Si la page VM n'est pas renseignée.
        """
        if self._keycloak is None:
            vm = self.config.vm
            if vm is None:
                raise RuntimeError("Configuration de la VM absente")
            self._keycloak = self._keycloak_factory(
                f"https://{vm.vm_ip}",
                "admin",
                self.store.secrets.keycloak_admin_password,
                host=f"keycloak.{vm.domain}",
            )
        return self._keycloak

    def node_ssh(self, node: str) -> SshSession:
        """Ouvre une session SSH sur un nœud Proxmox (mot de passe de la page 10).

        Args:
            node: Nom du nœud.

        Returns:
            La session connectée, fermée à la fin de l'installation.

        Raises:
            SshError: Si aucun accès n'est configuré pour ce nœud ou s'il est injoignable.
        """
        access = self.config.nodes.get(node)
        if access is None:
            raise SshError(f"Aucun accès SSH configuré pour le nœud {node}")
        session = self._ssh_factory(
            access.host or node, access.user, password=access.password
        )
        session.connect()
        self._sessions.append(session)
        return session

    def close(self) -> None:
        """Ferme les sessions SSH et abandonne le client Keycloak."""
        for session in self._sessions:
            session.close()
        self._sessions = []
        self._vm_ssh = None
        self._keycloak = None

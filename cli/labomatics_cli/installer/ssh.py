"""Accès SSH minimal (paramiko) et clé SSH du CLI."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Optional

import paramiko  # type: ignore[import-untyped]
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

DEFAULT_KEY_PATH = Path.home() / ".labomatics" / "ssh" / "labomatics-cli"


class SshError(Exception):
    """Erreur SSH avec un message directement affichable en français."""


@dataclass(frozen=True)
class CommandResult:
    """Résultat d'une commande distante."""

    stdout: str
    stderr: str
    code: int

    @property
    def ok(self) -> bool:
        """Indique si la commande a réussi.

        Returns:
            True si le code de retour est 0.
        """
        return self.code == 0


class CliKey:
    """Clé SSH ed25519 du CLI, générée au premier usage."""

    def __init__(self, path: Optional[Path] = None) -> None:
        """Initialise la clé.

        Args:
            path: Fichier de la clé privée (`~/.labomatics/ssh/labomatics-cli` par défaut).
        """
        self.path = path or DEFAULT_KEY_PATH

    @property
    def public_path(self) -> Path:
        """Fichier de la clé publique.

        Returns:
            Le chemin de la clé privée suffixé de « .pub ».
        """
        return self.path.with_name(self.path.name + ".pub")

    def ensure(self) -> Path:
        """Génère la paire de clés si la clé privée est absente.

        Returns:
            Le chemin de la clé privée.
        """
        if self.path.exists():
            return self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        key = ed25519.Ed25519PrivateKey.generate()
        private = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
        public = key.public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
        )
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(private)
        self.public_path.write_bytes(public + b" labomatics-cli\n")
        return self.path

    def public_key(self) -> str:
        """Clé publique, générée au besoin.

        Returns:
            La ligne `authorized_keys` de la clé du CLI.
        """
        self.ensure()
        return self.public_path.read_text().strip()


class SshSession:
    """Session SSH par clé ou mot de passe, utilisable avec `with`."""

    def __init__(
        self,
        host: str,
        user: str,
        *,
        password: Optional[str] = None,
        key_path: Optional[Path] = None,
        port: int = 22,
        timeout: int = 30,
        retries: int = 5,
        delay: float = 2.0,
    ) -> None:
        """Prépare la session (aucune connexion n'est ouverte).

        Args:
            host: Adresse ou nom de l'hôte.
            user: Utilisateur.
            password: Mot de passe (sinon la clé est utilisée).
            key_path: Fichier de la clé privée.
            port: Port SSH.
            timeout: Délai de connexion en secondes.
            retries: Nombre de tentatives de connexion.
            delay: Pause entre deux tentatives en secondes.
        """
        self.host = host
        self.user = user
        self.password = password
        self.key_path = key_path
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        """Ouvre la connexion avec plusieurs tentatives.

        Raises:
            SshError: Si l'hôte reste injoignable ou refuse l'authentification.
        """
        if self._client is not None:
            return
        last: Optional[Exception] = None
        for attempt in range(self.retries):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    key_filename=str(self.key_path) if self.key_path else None,
                    timeout=self.timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            except (paramiko.SSHException, OSError) as exc:
                last = exc
                client.close()
                if attempt < self.retries - 1:
                    time.sleep(self.delay)
            else:
                self._client = client
                return
        raise SshError(f"Connexion SSH impossible vers {self.host} : {last}")

    def close(self) -> None:
        """Ferme la connexion si elle est ouverte."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SshSession":
        """Ouvre la connexion en entrant dans le bloc `with`.

        Returns:
            La session connectée.
        """
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        """Ferme la connexion en sortant du bloc `with`.

        Args:
            exc_type: Type de l'exception éventuelle.
            exc: Exception éventuelle.
            tb: Trace éventuelle.
        """
        self.close()

    def _connected(self) -> paramiko.SSHClient:
        """Renvoie le client connecté.

        Returns:
            Le client paramiko.

        Raises:
            SshError: Si la session n'est pas connectée.
        """
        if self._client is None:
            raise SshError(f"Session SSH non connectée ({self.host})")
        return self._client

    def run(
        self, command: str, check: bool = True, timeout: int = 900
    ) -> CommandResult:
        """Exécute une commande distante.

        Args:
            command: Commande ou script shell.
            check: Lève une erreur si le code de retour n'est pas 0.
            timeout: Délai maximal de lecture en secondes.

        Returns:
            Sortie standard, sortie d'erreur et code de retour.

        Raises:
            SshError: Si `check` est vrai et que la commande échoue.
        """
        _, stdout, stderr = self._connected().exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        result = CommandResult(out, err, stdout.channel.recv_exit_status())
        if check and not result.ok:
            detail = (result.stderr or result.stdout).strip()
            raise SshError(
                f"Commande en échec sur {self.host} ({result.code}) : {detail}"
            )
        return result

    def put_text(self, path: str, content: str, mode: int = 0o644) -> None:
        """Écrit un fichier texte distant.

        Args:
            path: Chemin distant.
            content: Contenu du fichier.
            mode: Permissions du fichier.
        """
        sftp = self._connected().open_sftp()
        try:
            with sftp.open(path, "w") as handle:
                handle.write(content)
            sftp.chmod(path, mode)
        finally:
            sftp.close()

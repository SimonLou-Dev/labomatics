"""Téléchargement d'un fichier sur une machine distante, avec suivi de progression."""

from __future__ import annotations

import posixpath
import time
from urllib.parse import urlparse
from typing import Callable, Optional

from labomatics_cli.installer.ssh import SshSession

Log = Callable[[str], None]

FIRST_CHECK = 5


class RemoteDownload:
    """Lance `wget` en arrière-plan sur l'hôte distant et journalise la progression.

    Le fichier est écrit dans `<chemin>.part`, renommé une fois complet ; le code
    de retour de `wget` est déposé dans `<chemin>.rc`.
    """

    def __init__(
        self,
        ssh: SshSession,
        url: str,
        path: str,
        *,
        poll: float = 30,
        timeout: float = 1800,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialise le téléchargement.

        Args:
            ssh: Session SSH sur l'hôte qui télécharge.
            url: Adresse du fichier.
            path: Chemin final du fichier sur l'hôte.
            poll: Intervalle entre deux messages de progression, en secondes.
            timeout: Durée maximale du téléchargement, en secondes.
            sleep: Fonction d'attente, remplaçable en test.
        """
        self.ssh, self.url, self.path = ssh, url, path
        self.poll, self.timeout, self.sleep = poll, timeout, sleep
        self.part, self.rc, self.log_file = f"{path}.part", f"{path}.rc", f"{path}.log"

    def run(self, log: Log) -> None:
        """Télécharge le fichier et appelle `log` à chaque point de progression.

        Args:
            log: Reçoit les messages de progression.

        Raises:
            RuntimeError: Si l'hôte ne résout pas le serveur, si `wget` échoue
                ou si le délai est dépassé.
        """
        self._check_dns()
        total = self._total_size()
        self._start()
        size = f"{total // 1_000_000} Mo" if total else "taille inconnue"
        log(f"Téléchargement lancé ({size}), progression toutes les {self.poll:.0f} s")
        waited = 0.0
        while True:
            delay = min(FIRST_CHECK, self.poll) if waited == 0 else self.poll
            self.sleep(delay)
            waited += delay
            code = self._exit_code()
            if code is not None:
                self._finish(code)
                return
            if waited >= self.timeout:
                self.ssh.run(f"pkill -f '[w]get .*{self.part}'", check=False)
                raise RuntimeError(f"Téléchargement trop long (> {self.timeout:.0f} s)")
            log(self._progress(total))

    def _check_dns(self) -> None:
        """Vérifie que l'hôte résout le nom du serveur de téléchargement.

        Raises:
            RuntimeError: Si le nom ne se résout pas (DNS de l'hôte en panne).
        """
        server = urlparse(self.url).hostname or ""
        if not self.ssh.run(f"getent hosts {server}", check=False).ok:
            raise RuntimeError(
                f"Le nœud ne résout pas {server} : vérifie son DNS (/etc/resolv.conf)"
            )

    def _total_size(self) -> Optional[int]:
        """Taille annoncée par le serveur (après redirections).

        Returns:
            La taille en octets, ou None si le serveur ne l'indique pas.
        """
        result = self.ssh.run(
            f"curl -sIL --max-time 20 {self.url} | tr -d '\\r' | "
            "awk 'tolower($1)==\"content-length:\" {s=$2} END {print s}'",
            check=False,
        )
        text = result.stdout.strip()
        return int(text) if text.isdigit() and int(text) > 0 else None

    def _start(self) -> None:
        """Lance `wget` en arrière-plan, détaché de la session SSH."""
        folder = posixpath.dirname(self.path)
        self.ssh.run(
            f"mkdir -p {folder} && rm -f {self.part} {self.rc} {self.log_file} && "
            f"nohup sh -c 'wget -nv --tries=3 --timeout=60 -O {self.part} {self.url} "
            f"> {self.log_file} 2>&1; echo $? > {self.rc}' < /dev/null > /dev/null 2>&1 &"
        )

    def _exit_code(self) -> Optional[int]:
        """Code de retour de `wget`, s'il a terminé.

        Returns:
            Le code, ou None tant que le téléchargement tourne.
        """
        text = self.ssh.run(f"cat {self.rc}", check=False).stdout.strip()
        return int(text) if text.isdigit() else None

    def _progress(self, total: Optional[int]) -> str:
        """Message de progression courant.

        Args:
            total: Taille totale en octets, si connue.

        Returns:
            « Téléchargement : 45 % (210/480 Mo) » ou la taille reçue seule.
        """
        text = self.ssh.run(f"stat -c %s {self.part}", check=False).stdout.strip()
        done = int(text) if text.isdigit() else 0
        mb = done // 1_000_000
        if done == 0:
            last = self.ssh.run(f"tail -n 1 {self.log_file}", check=False).stdout
            return f"Téléchargement : rien reçu pour l'instant {last.strip()}".rstrip()
        if total:
            percent = min(100, done * 100 // total)
            return f"Téléchargement : {percent} % ({mb}/{total // 1_000_000} Mo)"
        return f"Téléchargement : {mb} Mo reçus"

    def _finish(self, code: int) -> None:
        """Renomme le fichier complet, ou remonte l'erreur de `wget`.

        Args:
            code: Code de retour de `wget`.

        Raises:
            RuntimeError: Si `wget` a échoué.
        """
        if code == 0:
            self.ssh.run(
                f"mv {self.part} {self.path} && rm -f {self.rc} {self.log_file}"
            )
            return
        tail = self.ssh.run(f"tail -n 3 {self.log_file}", check=False).stdout
        self.ssh.run(f"rm -f {self.part} {self.rc}", check=False)
        detail = " | ".join(tail.strip().splitlines()) or "aucune sortie"
        raise RuntimeError(f"wget a échoué (code {code}) : {detail}")

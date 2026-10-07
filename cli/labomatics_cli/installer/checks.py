"""Contrôles de connectivité du wizard : ping, SSH, LDAP, SMTP et Brevo."""

from __future__ import annotations

import smtplib
import socket
import subprocess
from dataclasses import dataclass, field

import paramiko  # type: ignore[import-untyped]
import requests
from ldap3 import BASE, NONE, Connection, Server
from ldap3.core.exceptions import LDAPException

BREVO_ACCOUNT_URL = "https://api.brevo.com/v3/account"


class CheckError(Exception):
    """Contrôle échoué, avec un message directement affichable en français."""


class PingCheck:
    """Test de joignabilité par ping."""

    def __init__(self, timeout: int = 2) -> None:
        """Initialise le contrôle.

        Args:
            timeout: Délai d'attente de la réponse en secondes.
        """
        self.timeout = timeout

    def is_alive(self, ip: str) -> bool:
        """Envoie un ping.

        Args:
            ip: Adresse à tester.

        Returns:
            True si l'adresse répond.
        """
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(self.timeout), ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.timeout + 3,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0


class SshCheck:
    """Test de connexion SSH par mot de passe."""

    def __init__(self, timeout: int = 10) -> None:
        """Initialise le contrôle.

        Args:
            timeout: Délai de connexion en secondes.
        """
        self.timeout = timeout

    def check(self, host: str, user: str, password: str) -> None:
        """Ouvre puis ferme une session SSH.

        Args:
            host: Adresse du nœud.
            user: Utilisateur SSH.
            password: Mot de passe SSH.

        Raises:
            CheckError: Si la connexion ou l'authentification échoue.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                host,
                username=user,
                password=password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        except paramiko.AuthenticationException as exc:
            raise CheckError(f"authentification refusée pour {user}@{host}") from exc
        except (paramiko.SSHException, OSError, socket.timeout) as exc:
            raise CheckError(f"{host} injoignable en SSH ({exc})") from exc
        finally:
            client.close()


class LdapCheck:
    """Test de bind LDAP et présence des branches utilisateurs et groupes."""

    def __init__(self, timeout: int = 10) -> None:
        """Initialise le contrôle.

        Args:
            timeout: Délai de connexion en secondes.
        """
        self.timeout = timeout

    def check(
        self, url: str, starttls: bool, bind_dn: str, password: str, base_dn: str
    ) -> None:
        """Se lie à l'annuaire puis vérifie `ou=users` et `ou=groups`.

        Args:
            url: URL `ldap://` ou `ldaps://`.
            starttls: Active StartTLS (ignoré en `ldaps://`).
            bind_dn: DN du compte de bind.
            password: Mot de passe du compte de bind.
            base_dn: DN de base de l'annuaire.

        Raises:
            CheckError: Si le bind échoue ou si une branche est absente.
        """
        server = Server(url, get_info=NONE, connect_timeout=self.timeout)
        try:
            conn = Connection(server, user=bind_dn, password=password)
            if not conn.open(read_server_info=False):
                raise CheckError(f"connexion LDAP impossible vers {url}")
            if starttls and not url.lower().startswith("ldaps://"):
                conn.start_tls(read_server_info=False)
            if not conn.bind():
                raise CheckError("bind LDAP refusé (DN ou mot de passe invalide)")
            try:
                for branch in (f"ou=users,{base_dn}", f"ou=groups,{base_dn}"):
                    found = conn.search(branch, "(objectClass=*)", search_scope=BASE)
                    if not found:
                        raise CheckError(f"branche LDAP introuvable : {branch}")
            finally:
                conn.unbind()
        except LDAPException as exc:
            raise CheckError(f"erreur LDAP : {exc}") from exc


class SmtpCheck:
    """Test de connexion et d'authentification SMTP."""

    def __init__(self, timeout: int = 10) -> None:
        """Initialise le contrôle.

        Args:
            timeout: Délai de connexion en secondes.
        """
        self.timeout = timeout

    def check(
        self, host: str, port: int, starttls: bool, user: str, password: str
    ) -> None:
        """Se connecte au serveur SMTP et s'authentifie si un utilisateur est fourni.

        Args:
            host: Serveur SMTP.
            port: Port SMTP (465 = TLS implicite).
            starttls: Active STARTTLS (ignoré sur le port 465).
            user: Utilisateur ; vide pour ne pas s'authentifier.
            password: Mot de passe SMTP.

        Raises:
            CheckError: Si la connexion ou l'authentification échoue.
        """
        try:
            if port == 465:
                smtp: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=self.timeout)
            else:
                smtp = smtplib.SMTP(host, port, timeout=self.timeout)
            with smtp:
                smtp.ehlo()
                if starttls and port != 465:
                    smtp.starttls()
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
        except smtplib.SMTPAuthenticationError as exc:
            raise CheckError("authentification SMTP refusée") from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise CheckError(f"SMTP {host}:{port} injoignable ({exc})") from exc


class BrevoCheck:
    """Test de la clé API Brevo."""

    def __init__(self, timeout: int = 10) -> None:
        """Initialise le contrôle.

        Args:
            timeout: Délai de la requête en secondes.
        """
        self.timeout = timeout

    def check(self, api_key: str) -> None:
        """Interroge `GET /v3/account`.

        Args:
            api_key: Clé API Brevo.

        Raises:
            CheckError: Si la clé est refusée ou Brevo injoignable.
        """
        try:
            response = requests.get(
                BREVO_ACCOUNT_URL, headers={"api-key": api_key}, timeout=self.timeout
            )
        except requests.exceptions.RequestException as exc:
            raise CheckError(f"Brevo injoignable ({exc})") from exc
        if response.status_code in (401, 403):
            raise CheckError("clé API Brevo invalide")
        if not response.ok:
            raise CheckError(f"Brevo a répondu {response.status_code}")


@dataclass
class Checks:
    """Ensemble des contrôles utilisés par les pages (remplaçable en test)."""

    ping: PingCheck = field(default_factory=PingCheck)
    ssh: SshCheck = field(default_factory=SshCheck)
    ldap: LdapCheck = field(default_factory=LdapCheck)
    smtp: SmtpCheck = field(default_factory=SmtpCheck)
    brevo: BrevoCheck = field(default_factory=BrevoCheck)

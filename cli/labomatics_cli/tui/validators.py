"""Validateurs : renvoient un message d'erreur en français, ou None si la valeur est valide."""

from __future__ import annotations

import base64
import binascii
import ipaddress
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any, Mapping
from urllib.parse import urlsplit

_LABEL = r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
_HOSTNAME_RE = re.compile(rf"^(?=.{{1,253}}$){_LABEL}(\.{_LABEL})*$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
_SSH_RE = re.compile(
    r"^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh\.com) "
    r"([A-Za-z0-9+/]+={0,3})( .*)?$"
)
_RDN = r"[A-Za-z][A-Za-z0-9-]*=[^,=]+"
_LDAP_DN_RE = re.compile(rf"^{_RDN}(,\s*{_RDN})*$")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")


def _text(value: Any) -> str:
    """Convertit une valeur en texte sans espaces autour.

    Args:
        value: Valeur à convertir.

    Returns:
        Le texte nettoyé.
    """
    return str(value).strip()


def _network(value: Any) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    """Interprète une valeur comme réseau, sans exiger une adresse réseau stricte.

    Args:
        value: Valeur à interpréter.

    Returns:
        Le réseau, ou None s'il est invalide.
    """
    try:
        return ipaddress.ip_network(_text(value), strict=False)
    except ValueError:
        return None


class Validator(ABC):
    """Contrôle une valeur ; renvoie un message d'erreur ou None."""

    @abstractmethod
    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """


class Ip(Validator):
    """Adresse IP v4 ou v6."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        try:
            ipaddress.ip_address(_text(value))
        except ValueError:
            return "Adresse IP invalide (ex. 192.168.1.10)"
        return None


class Cidr(Validator):
    """Réseau CIDR strict (adresse réseau, pas d'hôte)."""

    def __init__(self, max_prefix: int | None = None):
        """Initialise le validateur.

        Args:
            max_prefix: Longueur de préfixe maximale.
        """
        self.max_prefix = max_prefix

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        text = _text(value)
        if "/" not in text:
            return "Format attendu : réseau/masque (ex. 10.10.0.0/16)"
        try:
            network = ipaddress.ip_network(text, strict=True)
        except ValueError:
            loose = _network(text)
            if loose is None:
                return "Réseau invalide (ex. 10.10.0.0/16)"
            return f"Pas une adresse de réseau : utilise {loose}"
        if self.max_prefix is not None and network.prefixlen > self.max_prefix:
            return f"Préfixe trop long : /{self.max_prefix} maximum"
        return None


class IpRange(Validator):
    """Plage « a-b » de même version avec a <= b."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        parts = [p.strip() for p in _text(value).split("-")]
        if len(parts) != 2:
            return "Format attendu : ip-ip (ex. 10.0.0.10-10.0.0.50)"
        try:
            start, end = ipaddress.ip_address(parts[0]), ipaddress.ip_address(parts[1])
        except ValueError:
            return "Adresse IP invalide dans la plage"
        if start.version != end.version:
            return "Les deux IP doivent être de la même version"
        if int(start) > int(end):
            return "Le début de la plage doit être inférieur à la fin"
        return None


class IpOrRange(Validator):
    """Adresse IP ou plage « a-b »."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        if "-" in _text(value):
            return IpRange()(value, values)
        return Ip()(value, values)


class IpOrCidr(Validator):
    """Adresse IP ou réseau CIDR."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        if "/" in _text(value):
            return Cidr()(value, values)
        return Ip()(value, values)


class IpIn(Validator):
    """IP (ou bornes d'une plage) incluse dans le CIDR d'un autre champ."""

    def __init__(self, field_key: str, exclude_edges: bool = True):
        """Initialise le validateur.

        Args:
            field_key: Clé du champ de référence.
            exclude_edges: Interdit les adresses réseau et broadcast.
        """
        self.field_key = field_key
        self.exclude_edges = exclude_edges

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        raw = _text(values.get(self.field_key) or "")
        network = _network(raw) if "/" in raw else None
        for part in _text(value).split("-"):
            try:
                address = ipaddress.ip_address(part.strip())
            except ValueError:
                return "Adresse IP invalide"
            if network is None:
                continue
            if address.version != network.version or address not in network:
                return f"{address} est hors du réseau {network}"
            if self.exclude_edges and network.prefixlen < network.max_prefixlen - 1:
                if address in (network.network_address, network.broadcast_address):
                    return f"{address} est l'adresse réseau ou broadcast de {network}"
        return None


class NoOverlap(Validator):
    """Réseau CIDR sans chevauchement avec ceux d'autres champs."""

    def __init__(self, *field_keys: str):
        """Initialise le validateur."""
        self.field_keys = field_keys

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        mine = _network(value)
        if mine is None:
            return None
        for key in self.field_keys:
            other = values.get(key)
            for item in other if isinstance(other, (list, tuple)) else [other]:
                theirs = _network(item) if item else None
                if (
                    theirs is not None
                    and theirs.version == mine.version
                    and mine.overlaps(theirs)
                ):
                    return f"Chevauche le réseau {theirs}"
        return None


class Hostname(Validator):
    """Nom d'hôte, ou IP valide s'il ne contient que des chiffres et des points."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        text = _text(value)
        # "10.0.0.999" passerait la regex : une suite de chiffres doit être une IP valide
        if re.fullmatch(r"[\d.]+", text):
            return Ip()(text, values)
        return None if _HOSTNAME_RE.match(text) else "Nom d'hôte invalide"


class Host(Validator):
    """IP ou nom d'hôte."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        if Ip()(value, values) is None or Hostname()(value, values) is None:
            return None
        return "IP ou nom d'hôte invalide"


class Domain(Validator):
    """Nom de domaine d'au moins deux labels (« .local » accepté)."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        text = _text(value)
        if (
            re.fullmatch(r"[\d.]+", text)
            or not _HOSTNAME_RE.match(text)
            or "." not in text
        ):
            return "Nom de domaine invalide (ex. lab.example.com)"
        return None


class Url(Validator):
    """URL avec schéma autorisé et hôte valide."""

    def __init__(self, schemes: tuple[str, ...] = ("https",)):
        """Initialise le validateur.

        Args:
            schemes: Schémas autorisés.
        """
        self.schemes = schemes

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        expected = f"URL attendue : {'|'.join(self.schemes)}://hôte[:port]"
        try:
            parts = urlsplit(_text(value))
            host, _ = parts.hostname, parts.port
        except ValueError:
            return expected
        if parts.scheme not in self.schemes or not host or Host()(host, values):
            return expected
        return None


class Email(Validator):
    """Adresse e-mail."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        return None if _EMAIL_RE.match(_text(value)) else "Adresse e-mail invalide"


class Port(Validator):
    """Port TCP/UDP entre 1 et 65535."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        text = _text(value)
        if text.isdigit() and 1 <= int(text) <= 65535:
            return None
        return "Port entre 1 et 65535"


class IntRange(Validator):
    """Entier dans un intervalle."""

    def __init__(self, min: int | None = None, max: int | None = None):
        """Initialise le validateur.

        Args:
            min: Borne minimale.
            max: Borne maximale.
        """
        self.min = min
        self.max = max

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        try:
            number = int(_text(value))
        except ValueError:
            return "Nombre entier attendu"
        if self.min is not None and number < self.min:
            return f"{self.min} minimum"
        if self.max is not None and number > self.max:
            return f"{self.max} maximum"
        return None


class GreaterThan(Validator):
    """Entier strictement supérieur à celui d'un autre champ."""

    def __init__(self, field_key: str):
        """Initialise le validateur.

        Args:
            field_key: Clé du champ de référence.
        """
        self.field_key = field_key

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        try:
            number = int(_text(value))
        except ValueError:
            return "Nombre entier attendu"
        try:
            other = int(_text(values.get(self.field_key, "")))
        except ValueError:
            return None
        return None if number > other else f"Doit être supérieur à {other}"


class Length(Validator):
    """Longueur de texte bornée."""

    def __init__(self, min: int = 0, max: int | None = None):
        """Initialise le validateur.

        Args:
            min: Borne minimale.
            max: Borne maximale.
        """
        self.min = min
        self.max = max

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        size = len(str(value))
        if size < self.min:
            return f"{self.min} caractères minimum"
        if self.max is not None and size > self.max:
            return f"{self.max} caractères maximum"
        return None


class Regex(Validator):
    """Texte qui correspond entièrement à une expression régulière."""

    def __init__(self, pattern: str, message: str):
        """Initialise le validateur.

        Args:
            pattern: Expression régulière.
            message: Message d'erreur.
        """
        self.pattern = re.compile(pattern)
        self.message = message

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        return None if self.pattern.fullmatch(str(value)) else self.message


class SshPublicKey(Validator):
    """Clé publique SSH (ed25519, rsa, ecdsa) en base64."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        error = "Clé publique SSH invalide (ssh-ed25519, ssh-rsa ou ecdsa-sha2-*)"
        match = _SSH_RE.match(_text(value))
        if not match:
            return error
        try:
            base64.b64decode(match.group(3), validate=True)
        except binascii.Error:
            return error
        return None


class LdapDn(Validator):
    """DN LDAP (ex. dc=example,dc=com)."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        if _LDAP_DN_RE.match(_text(value)):
            return None
        return "DN LDAP invalide (ex. dc=example,dc=com)"


class LdapUrl(Validator):
    """URL LDAP « ldap(s)://hôte[:port] »."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        error = "URL LDAP invalide (ex. ldaps://ldap.example.com:636)"
        match = re.fullmatch(r"ldaps?://([^:/]+)(?::(\d+))?", _text(value))
        if not match or Host()(match.group(1), values):
            return error
        if match.group(2) and Port()(match.group(2), values):
            return error
        return None


class Uuid(Validator):
    """UUID au format canonique."""

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        text = _text(value)
        if _UUID_RE.match(text):
            uuid.UUID(text)
            return None
        return "UUID invalide"


class AllOf(Validator):
    """Combine des validateurs ; renvoie la première erreur."""

    def __init__(self, *validators: Validator):
        """Initialise le validateur."""
        self.validators = validators

    def __call__(self, value: Any, values: Mapping[str, Any]) -> str | None:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie à contrôler.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur en français, ou None si la valeur est valide.
        """
        for validator in self.validators:
            error = validator(value, values)
            if error:
                return error
        return None

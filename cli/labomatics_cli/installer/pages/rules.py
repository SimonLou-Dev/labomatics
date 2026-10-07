"""Règles de validation propres aux pages d'installation."""

from __future__ import annotations

import ipaddress
from typing import Any, Callable, Collection, Mapping, Optional

from labomatics_cli.tui.validators import Validator


class DifferentFrom(Validator):
    """Valeur différente de celle d'un autre champ."""

    def __init__(self, field_key: str, name: str) -> None:
        """Initialise la règle.

        Args:
            field_key: Clé du champ à ne pas égaler.
            name: Nom affiché dans le message (ex. « la passerelle »).
        """
        self.field_key = field_key
        self.name = name

    def __call__(self, value: Any, values: Mapping[str, Any]) -> Optional[str]:
        """Contrôle la valeur.

        Args:
            value: Valeur saisie.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur, ou None si la valeur est valide.
        """
        if str(value).strip() == str(values.get(self.field_key) or "").strip():
            return f"Doit être différent de {self.name}"
        return None


class FreeClusterName(Validator):
    """Nom de cluster qui n'existe pas encore."""

    def __init__(self, taken: Callable[[], Collection[str]]) -> None:
        """Initialise la règle.

        Args:
            taken: Fonction renvoyant les noms déjà utilisés (vide si le cluster est ouvert).
        """
        self.taken = taken

    def __call__(self, value: Any, values: Mapping[str, Any]) -> Optional[str]:
        """Contrôle la valeur.

        Args:
            value: Nom saisi.
            values: Valeurs des autres champs, par clé.

        Returns:
            Un message d'erreur, ou None si le nom est libre.
        """
        if str(value).strip() in self.taken():
            return "Un cluster de ce nom existe déjà : relance sans --cluster pour le choisir"
        return None


class AddressPool:
    """Adresses allouables d'un réseau, une fois la passerelle et les exclusions retirées."""

    def __init__(self, network: str, gateway: str, exclusions: list[str]) -> None:
        """Initialise le calcul.

        Args:
            network: Réseau CIDR.
            gateway: Adresse de la passerelle.
            exclusions: IP ou plages « a-b » exclues.
        """
        self.network = ipaddress.ip_network(network, strict=False)
        self.gateway = gateway
        self.exclusions = exclusions

    def free_count(self) -> int:
        """Compte les adresses allouables.

        Returns:
            Le nombre d'IP libres (réseau et broadcast exclus).
        """
        net = self.network
        edge = 1 if net.prefixlen < net.max_prefixlen - 1 else 0
        first = int(net.network_address) + edge
        last = int(net.broadcast_address) - edge
        taken = self._merge(
            [
                self._interval(item, first, last)
                for item in [self.gateway, *self.exclusions]
            ]
        )
        return (last - first + 1) - sum(end - start + 1 for start, end in taken)

    @staticmethod
    def _interval(item: str, first: int, last: int) -> Optional[tuple[int, int]]:
        """Convertit une IP ou une plage en intervalle borné au réseau.

        Args:
            item: IP ou plage « a-b ».
            first: Première adresse allouable.
            last: Dernière adresse allouable.

        Returns:
            L'intervalle (début, fin), ou None s'il est hors du réseau.
        """
        start_text, _, end_text = item.partition("-")
        start = int(ipaddress.ip_address(start_text.strip()))
        end = int(ipaddress.ip_address((end_text or start_text).strip()))
        start, end = max(start, first), min(end, last)
        return (start, end) if start <= end else None

    @staticmethod
    def _merge(intervals: list[Optional[tuple[int, int]]]) -> list[tuple[int, int]]:
        """Fusionne les intervalles qui se chevauchent.

        Args:
            intervals: Intervalles (ou None à ignorer).

        Returns:
            Les intervalles disjoints triés.
        """
        merged: list[tuple[int, int]] = []
        for start, end in sorted(i for i in intervals if i is not None):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

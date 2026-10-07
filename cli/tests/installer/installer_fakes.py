"""Faux utilisés par les tests de l'installeur : client proxmoxer, contrôles réseau, API."""

from typing import Any, Optional

from labomatics_cli.installer.checks import CheckError, Checks
from labomatics_cli.installer.proxmox_api import Bridge, ProxmoxNode, Storage

UUID = "12345678-1234-1234-1234-123456789abc"

CLUSTER_DATA: dict[str, Any] = {
    "version": {"version": "8.2.4"},
    "cluster/status": [
        {"type": "cluster", "name": "pvecl"},
        {"type": "node", "name": "pve1", "ip": "10.0.0.11"},
        {"type": "node", "name": "pve2", "ip": "10.0.0.12"},
    ],
    "nodes": [
        {"node": "pve1", "status": "online"},
        {"node": "pve2", "status": "online"},
    ],
    "access/permissions": {
        "/": {
            "Sys.Modify": 1,
            "VM.Allocate": 1,
            "SDN.Allocate": 1,
            "Permissions.Modify": 1,
            "Realm.Allocate": 1,
        }
    },
    "nodes/pve1/network": [
        {"iface": "vmbr0", "type": "bridge", "cidr": "10.100.25.1/24"},
        {"iface": "vmbr1", "type": "bridge"},
        {"iface": "eno1", "type": "eth"},
    ],
    "nodes/pve2/network": [
        {"iface": "vmbr0", "type": "bridge"},
        {"iface": "vmbr2", "type": "bridge"},
    ],
    "storage": [
        {"storage": "local", "type": "dir", "content": "iso,vztmpl"},
        {"storage": "ceph", "type": "rbd", "content": "images,rootdir", "shared": 1},
        {"storage": "nfs", "type": "nfs", "content": "iso", "shared": 1},
        {
            "storage": "part",
            "type": "rbd",
            "content": "images",
            "shared": 1,
            "nodes": "pve1",
        },
    ],
    "cluster/sdn/zones": [
        {"zone": "labo", "type": "vxlan"},
        {"zone": "x", "type": "evpn"},
    ],
}


class FakeResource:
    """Ressource proxmoxer factice : accumule le chemin puis répond à `get`."""

    def __init__(self, data: dict[str, Any], path: str = "") -> None:
        """Initialise la ressource.

        Args:
            data: Réponses par chemin (« nodes/pve1/network »).
            path: Chemin accumulé.
        """
        self._data = data
        self._path = path

    def __getattr__(self, name: str) -> "FakeResource":
        """Descend d'un niveau dans le chemin.

        Args:
            name: Segment de chemin.

        Returns:
            La sous-ressource.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        return FakeResource(self._data, f"{self._path}/{name}".strip("/"))

    def get(self, **params: Any) -> Any:
        """Renvoie la réponse du chemin, ou lève l'exception enregistrée.

        Args:
            **params: Paramètres de requête (ignorés).

        Returns:
            La réponse enregistrée.
        """
        value = self._data[self._path]
        if isinstance(value, Exception):
            raise value
        return value


class FakeClientFactory:
    """Constructeur de client proxmoxer factice qui mémorise ses arguments."""

    def __init__(self, data: Optional[dict[str, Any]] = None) -> None:
        """Initialise la fabrique.

        Args:
            data: Réponses par chemin ; `CLUSTER_DATA` par défaut.
        """
        self.data = dict(CLUSTER_DATA if data is None else data)
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> FakeResource:
        """Construit le faux client.

        Args:
            *args: Arguments positionnels (hôte).
            **kwargs: Arguments nommés (port, user, token…).

        Returns:
            La ressource racine.
        """
        self.calls.append((args, kwargs))
        return FakeResource(self.data)


class FakeApi:
    """Faux `ProxmoxApi` complet, sans réseau."""

    def __init__(
        self, nodes: Optional[list[ProxmoxNode]] = None, missing: Optional[list] = None
    ) -> None:
        """Initialise l'API.

        Args:
            nodes: Nœuds renvoyés ; deux nœuds en ligne par défaut.
            missing: Privilèges manquants renvoyés.
        """
        self._nodes = nodes or [
            ProxmoxNode("pve1", "online", "10.0.0.11"),
            ProxmoxNode("pve2", "online", "10.0.0.12"),
        ]
        self._missing = missing or []
        self.zones: dict[str, str] = {}

    def version(self) -> str:
        """Version factice.

        Returns:
            « 8.2.4 ».
        """
        return "8.2.4"

    def nodes(self) -> list[ProxmoxNode]:
        """Nœuds factices.

        Returns:
            Les nœuds configurés.
        """
        return self._nodes

    def missing_privileges(self) -> list[str]:
        """Privilèges manquants factices.

        Returns:
            La liste configurée.
        """
        return self._missing

    def common_bridges(self) -> list[Bridge]:
        """Bridges communs factices.

        Returns:
            vmbr0 avec IP et vmbr1 sans IP.
        """
        return [Bridge("vmbr0", "10.100.25.1/24"), Bridge("vmbr1")]

    def shared_storages(self) -> list[Storage]:
        """Stockages partagés factices.

        Returns:
            Un stockage Ceph.
        """
        return [Storage("ceph", "rbd")]

    def sdn_zone(self, zone: str) -> Optional[str]:
        """Type de zone factice.

        Args:
            zone: Nom de la zone.

        Returns:
            Le type configuré, ou None.
        """
        return self.zones.get(zone)


class FakePing:
    """Ping factice : seules les adresses de `alive` répondent."""

    def __init__(self, alive: tuple[str, ...] = ()) -> None:
        """Initialise le faux ping.

        Args:
            alive: Adresses qui répondent.
        """
        self.alive = alive

    def is_alive(self, ip: str) -> bool:
        """Simule un ping.

        Args:
            ip: Adresse testée.

        Returns:
            True si l'adresse est dans `alive`.
        """
        return ip in self.alive


class FakeCheck:
    """Contrôle factice : enregistre ses appels et peut échouer."""

    def __init__(self, error: Optional[str] = None, fail_for: tuple = ()) -> None:
        """Initialise le contrôle.

        Args:
            error: Message d'erreur levé à chaque appel, ou None.
            fail_for: Premiers arguments (hôte) pour lesquels l'appel échoue.
        """
        self.error = error
        self.fail_for = fail_for
        self.calls: list[tuple] = []

    def check(self, *args: Any) -> None:
        """Enregistre l'appel et lève une erreur si configurée.

        Args:
            *args: Arguments du contrôle.

        Raises:
            CheckError: Si l'erreur est configurée ou l'hôte est dans `fail_for`.
        """
        self.calls.append(args)
        if self.error or (args and args[0] in self.fail_for):
            raise CheckError(self.error or "échec")


def fake_checks(alive: tuple[str, ...] = ()) -> Checks:
    """Construit un jeu de contrôles factices.

    Args:
        alive: Adresses qui répondent au ping.

    Returns:
        Les contrôles factices.
    """
    return Checks(
        ping=FakePing(alive),  # type: ignore[arg-type]
        ssh=FakeCheck(),  # type: ignore[arg-type]
        ldap=FakeCheck(),  # type: ignore[arg-type]
        smtp=FakeCheck(),  # type: ignore[arg-type]
        brevo=FakeCheck(),  # type: ignore[arg-type]
    )

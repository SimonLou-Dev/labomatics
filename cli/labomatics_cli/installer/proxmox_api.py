"""Client Proxmox minimal pour le wizard d'installation (lecture seule)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import requests
from proxmoxer import ProxmoxAPI  # type: ignore
from proxmoxer.core import ResourceException  # type: ignore

DEFAULT_PORT = 8006
REQUIRED_PRIVILEGES = (
    "Sys.Modify",
    "VM.Allocate",
    "SDN.Allocate",
    "Permissions.Modify",
    "Realm.Allocate",
)


class ProxmoxError(Exception):
    """Erreur Proxmox avec un message directement affichable en français."""


class ProxmoxConnectionError(ProxmoxError):
    """Cluster injoignable (réseau, TLS ou délai dépassé)."""


class ProxmoxAuthError(ProxmoxError):
    """Authentification refusée (HTTP 401)."""


class ProxmoxPermissionError(ProxmoxError):
    """Droits insuffisants (HTTP 403 ou privilèges manquants)."""


@dataclass(frozen=True)
class ProxmoxNode:
    """Nœud du cluster."""

    name: str
    status: str
    ip: str

    @property
    def online(self) -> bool:
        """Indique si le nœud est en ligne.

        Returns:
            True si son statut est « online ».
        """
        return self.status == "online"


@dataclass(frozen=True)
class Bridge:
    """Bridge réseau d'un nœud, avec son adresse CIDR éventuelle."""

    name: str
    cidr: Optional[str] = None

    @property
    def label(self) -> str:
        """Libellé d'affichage.

        Returns:
            « vmbr0 (10.100.25.1/24) » ou « vmbr0 (sans IP) ».
        """
        return f"{self.name} ({self.cidr or 'sans IP'})"


@dataclass(frozen=True)
class Storage:
    """Stockage Proxmox."""

    name: str
    type: str

    @property
    def label(self) -> str:
        """Libellé d'affichage.

        Returns:
            « nom (type) ».
        """
        return f"{self.name} ({self.type})"


class ProxmoxApi:
    """Lecture de l'API Proxmox par jeton, avec erreurs traduites en français."""

    def __init__(
        self,
        url: str,
        user: str,
        token_id: str,
        token_secret: str,
        *,
        timeout: int = 10,
        client_factory: Callable[..., Any] = ProxmoxAPI,
    ) -> None:
        """Prépare le client (aucune requête n'est envoyée).

        Args:
            url: URL du cluster ; le port est conservé (8006 par défaut).
            user: Utilisateur du jeton, « utilisateur@realm ».
            token_id: Nom du jeton (partie après le « ! »).
            token_secret: Secret du jeton.
            timeout: Délai maximal par requête en secondes.
            client_factory: Constructeur du client proxmoxer (remplaçable en test).
        """
        parts = urlsplit(url if "//" in url else f"https://{url}")
        self.host = parts.hostname or ""
        self.port = parts.port or DEFAULT_PORT
        self._client = client_factory(
            self.host,
            port=self.port,
            user=user,
            token_name=token_id,
            token_value=token_secret,
            verify_ssl=False,
            timeout=timeout,
        )

    def _get(self, path: str, **params: Any) -> Any:
        """Envoie un GET et traduit les erreurs.

        Args:
            path: Chemin de l'API sans « / » initial (ex. « nodes/pve1/network »).
            **params: Paramètres de requête.

        Returns:
            La réponse décodée.

        Raises:
            ProxmoxConnectionError: Réseau, TLS ou délai.
            ProxmoxAuthError: Jeton refusé (401).
            ProxmoxPermissionError: Droits insuffisants (403).
            ProxmoxError: Toute autre erreur de l'API.
        """
        resource = self._client
        for part in path.split("/"):
            resource = getattr(resource, part)
        try:
            return resource.get(**params)
        except ResourceException as exc:
            raise self._translate(exc) from exc
        except requests.exceptions.SSLError as exc:
            raise ProxmoxConnectionError(
                f"Erreur TLS vers {self.host}:{self.port} : {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ProxmoxConnectionError(
                f"Délai dépassé vers {self.host}:{self.port}"
            ) from exc
        except (requests.exceptions.RequestException, OSError) as exc:
            raise ProxmoxConnectionError(
                f"Impossible de joindre {self.host}:{self.port} : {exc}"
            ) from exc

    @staticmethod
    def _translate(exc: ResourceException) -> ProxmoxError:
        """Convertit une erreur HTTP de l'API en exception française.

        Args:
            exc: Erreur levée par proxmoxer.

        Returns:
            L'exception correspondante.
        """
        code = getattr(exc, "status_code", None)
        if code == 401:
            return ProxmoxAuthError("Authentification refusée (401) : jeton invalide")
        if code == 403:
            return ProxmoxPermissionError(
                "Accès refusé (403) : droits insuffisants pour ce jeton"
            )
        reason = getattr(exc, "status_reason", "") or str(exc)
        return ProxmoxError(f"Erreur Proxmox {code} : {reason}")

    def version(self) -> str:
        """Version de Proxmox VE.

        Returns:
            Par exemple « 8.2.4 ».
        """
        return str(self._get("version").get("version", ""))

    def cluster_name(self) -> Optional[str]:
        """Nom du cluster Proxmox.

        Returns:
            Le nom, ou None pour un nœud isolé.
        """
        for item in self._get("cluster/status"):
            if item.get("type") == "cluster":
                return item.get("name")
        return None

    def nodes(self) -> list[ProxmoxNode]:
        """Nœuds du cluster avec leur statut et leur IP.

        Returns:
            Les nœuds triés par nom ; l'IP est vide si elle est inconnue.
        """
        ips = {
            i["name"]: i.get("ip", "")
            for i in self._get("cluster/status")
            if i.get("type") == "node"
        }
        nodes = [
            ProxmoxNode(n["node"], n.get("status", "unknown"), ips.get(n["node"], ""))
            for n in self._get("nodes")
        ]
        if len(nodes) == 1 and not nodes[0].ip:
            nodes = [ProxmoxNode(nodes[0].name, nodes[0].status, self.host)]
        return sorted(nodes, key=lambda n: n.name)

    def permissions(self) -> dict[str, dict[str, int]]:
        """Permissions effectives du jeton.

        Returns:
            Les privilèges par chemin (ex. `{"/": {"Sys.Modify": 1}}`).
        """
        return self._get("access/permissions")

    def missing_privileges(self) -> list[str]:
        """Privilèges d'administration absents sur « / ».

        Returns:
            Les privilèges requis que le jeton n'a pas.
        """
        root = self.permissions().get("/", {})
        return [p for p in REQUIRED_PRIVILEGES if not root.get(p)]

    def bridges(self, node: str) -> list[Bridge]:
        """Bridges d'un nœud.

        Args:
            node: Nom du nœud.

        Returns:
            Les bridges Linux et OVS avec leur CIDR éventuel.
        """
        found = []
        for item in self._get(f"nodes/{node}/network"):
            if item.get("type") in ("bridge", "OVSBridge"):
                found.append(Bridge(item["iface"], item.get("cidr") or None))
        return sorted(found, key=lambda b: b.name)

    def common_bridges(self) -> list[Bridge]:
        """Bridges présents sur tous les nœuds.

        Returns:
            Les bridges communs, avec le CIDR du premier nœud qui en a un.
        """
        per_node = [self.bridges(n.name) for n in self.nodes()]
        if not per_node:
            return []
        common = set.intersection(*({b.name for b in bridges} for bridges in per_node))
        result = []
        for name in sorted(common):
            cidrs = [b.cidr for bridges in per_node for b in bridges if b.name == name]
            result.append(Bridge(name, next((c for c in cidrs if c), None)))
        return result

    def shared_storages(self) -> list[Storage]:
        """Stockages partagés pouvant contenir des disques de VM sur tous les nœuds.

        Returns:
            Les stockages `shared=1`, de contenu `images`, présents sur tous les nœuds.
        """
        names = {n.name for n in self.nodes()}
        found = []
        for item in self._get("storage"):
            content = str(item.get("content", "")).split(",")
            allowed = {n for n in str(item.get("nodes", "")).split(",") if n}
            if (
                item.get("shared")
                and not item.get("disable")
                and "images" in content
                and (not allowed or names <= allowed)
            ):
                found.append(Storage(item["storage"], item.get("type", "")))
        return sorted(found, key=lambda s: s.name)

    def sdn_zone(self, zone: str) -> Optional[str]:
        """Type d'une zone SDN.

        Args:
            zone: Nom de la zone.

        Returns:
            Son type (ex. « vxlan »), ou None si elle n'existe pas.
        """
        for item in self._get("cluster/sdn/zones"):
            if item.get("zone") == zone:
                return item.get("type")
        return None

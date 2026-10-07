"""Client Proxmox pour le wizard et les tâches d'installation."""

from __future__ import annotations

import time
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


@dataclass(frozen=True)
class VmInfo:
    """VM du cluster."""

    vmid: int
    node: str
    name: str
    status: str


class ProxmoxApi:
    """Accès à l'API Proxmox par jeton, avec erreurs traduites en français."""

    def __init__(
        self,
        url: str,
        user: str,
        token_id: str,
        token_secret: str,
        *,
        timeout: int = 10,
        poll_interval: float = 1.0,
        client_factory: Callable[..., Any] = ProxmoxAPI,
    ) -> None:
        """Prépare le client (aucune requête n'est envoyée).

        Args:
            url: URL du cluster ; le port est conservé (8006 par défaut).
            user: Utilisateur du jeton, « utilisateur@realm ».
            token_id: Nom du jeton (partie après le « ! »).
            token_secret: Secret du jeton.
            timeout: Délai maximal par requête en secondes.
            poll_interval: Pause entre deux lectures de l'état d'une tâche (secondes).
            client_factory: Constructeur du client proxmoxer (remplaçable en test).
        """
        parts = urlsplit(url if "//" in url else f"https://{url}")
        self.host = parts.hostname or ""
        self.port = parts.port or DEFAULT_PORT
        self.poll_interval = poll_interval
        self._client = client_factory(
            self.host,
            port=self.port,
            user=user,
            token_name=token_id,
            token_value=token_secret,
            verify_ssl=False,
            timeout=timeout,
        )

    def _request(self, verb: str, path: str, /, **params: Any) -> Any:
        """Envoie une requête et traduit les erreurs.

        Args:
            verb: Méthode proxmoxer (« get », « post », « put » ou « delete »).
            path: Chemin de l'API sans « / » initial (ex. « nodes/pve1/network »).
            **params: Paramètres de requête ou de corps.

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
            return getattr(resource, verb)(**params)
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

    def _get(self, path: str, /, **params: Any) -> Any:
        """Envoie un GET et traduit les erreurs.

        Args:
            path: Chemin de l'API sans « / » initial.
            **params: Paramètres de requête.

        Returns:
            La réponse décodée.

        Raises:
            ProxmoxError: Voir `_request`.
        """
        return self._request("get", path, **params)

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

    def user_exists(self, userid: str) -> bool:
        """Indique si un utilisateur existe.

        Args:
            userid: Identifiant « utilisateur@realm ».

        Returns:
            True si l'utilisateur existe.
        """
        return any(u.get("userid") == userid for u in self._get("access/users"))

    def create_user(
        self, userid: str, comment: str = "", email: Optional[str] = None
    ) -> None:
        """Crée un utilisateur sans mot de passe.

        Args:
            userid: Identifiant « utilisateur@realm ».
            comment: Commentaire facultatif.
            email: Adresse e-mail facultative.
        """
        params: dict[str, str] = {"comment": comment} if comment else {}
        if email:
            params["email"] = email
        self._request("post", "access/users", userid=userid, **params)

    def token_exists(self, userid: str, token: str) -> bool:
        """Indique si un jeton d'API existe.

        Args:
            userid: Utilisateur propriétaire.
            token: Nom du jeton.

        Returns:
            True si le jeton existe.
        """
        tokens = self._get(f"access/users/{userid}/token")
        return any(t.get("tokenid") == token for t in tokens)

    def delete_token(self, userid: str, token: str) -> None:
        """Supprime un jeton d'API.

        Args:
            userid: Utilisateur propriétaire.
            token: Nom du jeton.
        """
        self._request("delete", f"access/users/{userid}/token/{token}")

    def create_token(self, userid: str, token: str) -> str:
        """Crée un jeton sans séparation de privilèges.

        Args:
            userid: Utilisateur propriétaire.
            token: Nom du jeton.

        Returns:
            Le secret du jeton (visible une seule fois).
        """
        result = self._request(
            "post", f"access/users/{userid}/token/{token}", privsep=0
        )
        return str(result["value"])

    def grant(self, path: str, userid: str, role: str) -> None:
        """Attribue un rôle sur un chemin, avec propagation.

        Args:
            path: Chemin de l'ACL (ex. « / »).
            userid: Utilisateur ou « utilisateur@realm!jeton ».
            role: Nom du rôle.
        """
        self._request(
            "put", "access/acl", path=path, users=userid, roles=role, propagate=1
        )

    def create_sdn_zone(self, zone: str, peers: list[str], mtu: int) -> None:
        """Crée une zone SDN VXLAN.

        Args:
            zone: Nom de la zone.
            peers: Adresses IP des nœuds.
            mtu: MTU de la zone.
        """
        self._request(
            "post",
            "cluster/sdn/zones",
            zone=zone,
            type="vxlan",
            peers=",".join(peers),
            mtu=mtu,
        )

    def apply_sdn(self) -> str:
        """Applique la configuration SDN.

        Returns:
            L'identifiant (UPID) de la tâche lancée.
        """
        return str(self._request("put", "cluster/sdn"))

    def wait_task(self, upid: str, timeout: float = 300) -> None:
        """Attend la fin d'une tâche Proxmox.

        Args:
            upid: Identifiant de la tâche (le nœud en est extrait).
            timeout: Durée maximale d'attente en secondes.

        Raises:
            ProxmoxError: Si la tâche échoue ou dépasse le délai.
        """
        node = upid.split(":")[1]
        deadline = time.monotonic() + timeout
        while True:
            status = self._get(f"nodes/{node}/tasks/{upid}/status")
            if status.get("status") == "stopped":
                if status.get("exitstatus") != "OK":
                    raise ProxmoxError(
                        f"Tâche Proxmox en échec : {status.get('exitstatus')}"
                    )
                return
            if time.monotonic() >= deadline:
                raise ProxmoxError("Délai dépassé pour une tâche Proxmox")
            time.sleep(self.poll_interval)

    def find_vm(self, name: str) -> Optional[VmInfo]:
        """Cherche une VM par son nom.

        Args:
            name: Nom de la VM.

        Returns:
            La VM, ou None si elle n'existe pas.
        """
        for item in self._get("cluster/resources", type="vm"):
            if item.get("name") == name:
                return VmInfo(
                    int(item["vmid"]),
                    item.get("node", ""),
                    name,
                    item.get("status", "unknown"),
                )
        return None

    def next_vmid(self) -> int:
        """Premier VMID libre du cluster.

        Returns:
            Le VMID.
        """
        return int(self._get("cluster/nextid"))

    def create_vm(self, node: str, vmid: int, **options: Any) -> str:
        """Crée une VM.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.
            **options: Options de configuration Proxmox.

        Returns:
            L'identifiant (UPID) de la tâche.
        """
        return str(self._request("post", f"nodes/{node}/qemu", vmid=vmid, **options))

    def vm_config(self, node: str, vmid: int) -> dict[str, Any]:
        """Configuration d'une VM.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.

        Returns:
            Les options de la VM.
        """
        return dict(self._get(f"nodes/{node}/qemu/{vmid}/config"))

    def set_vm_config(self, node: str, vmid: int, **options: Any) -> None:
        """Modifie la configuration d'une VM.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.
            **options: Options à appliquer.
        """
        self._request("put", f"nodes/{node}/qemu/{vmid}/config", **options)

    def attach_unused_disk(self, node: str, vmid: int, disk: str) -> None:
        """Attache le premier disque `unusedN` (issu d'un `qm importdisk`) et le rend amorçable.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.
            disk: Emplacement cible (ex. « scsi0 »).

        Raises:
            ProxmoxError: Si la VM n'a aucun disque non utilisé.
        """
        config = self.vm_config(node, vmid)
        unused = sorted(k for k in config if k.startswith("unused"))
        if not unused:
            raise ProxmoxError(f"Aucun disque importé trouvé sur la VM {vmid}")
        self.set_vm_config(
            node, vmid, **{disk: config[unused[0]], "boot": f"order={disk}"}
        )

    def resize_disk(self, node: str, vmid: int, disk: str, size: str) -> None:
        """Redimensionne un disque de VM.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.
            disk: Disque (ex. « scsi0 »).
            size: Taille cible (ex. « 50G »).
        """
        self._request("put", f"nodes/{node}/qemu/{vmid}/resize", disk=disk, size=size)

    def vm_status(self, node: str, vmid: int) -> str:
        """État courant d'une VM.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.

        Returns:
            Par exemple « running » ou « stopped ».
        """
        return str(self._get(f"nodes/{node}/qemu/{vmid}/status/current")["status"])

    def start_vm(self, node: str, vmid: int) -> str:
        """Démarre une VM.

        Args:
            node: Nœud hôte.
            vmid: Identifiant de la VM.

        Returns:
            L'identifiant (UPID) de la tâche.
        """
        return str(self._request("post", f"nodes/{node}/qemu/{vmid}/status/start"))

    def node_dns(self, node: str) -> dict[str, str]:
        """Configuration DNS d'un nœud.

        Args:
            node: Nom du nœud.

        Returns:
            Les clés `dns1`, `search`… présentes.
        """
        return dict(self._get(f"nodes/{node}/dns"))

    def set_node_dns(self, node: str, dns1: str, search: str) -> None:
        """Configure le DNS d'un nœud.

        Args:
            node: Nom du nœud.
            dns1: Serveur DNS principal.
            search: Domaine de recherche.
        """
        self._request("put", f"nodes/{node}/dns", dns1=dns1, search=search)

    def node_fqdns(self, node: str) -> list[str]:
        """Noms de domaine ACME configurés sur un nœud.

        Args:
            node: Nom du nœud.

        Returns:
            Les FQDN trouvés dans `acmedomain0` à `acmedomain5`.
        """
        config = self._get(f"nodes/{node}/config")
        found: list[str] = []
        for index in range(6):
            raw = str(config.get(f"acmedomain{index}", ""))
            for part in raw.split(","):
                value = part.removeprefix("domain=").strip()
                if value and "=" not in value and value not in found:
                    found.append(value)
        return found

    def realm_exists(self, realm: str) -> bool:
        """Indique si un realm d'authentification existe.

        Args:
            realm: Nom du realm (ex. « labomatics »).

        Returns:
            True si le realm est déclaré dans `/access/domains`.
        """
        return any(d.get("realm") == realm for d in self._get("access/domains"))

    def configure_oidc_realm(
        self, realm: str, issuer_url: str, client_id: str, client_key: str
    ) -> bool:
        """Crée ou met à jour un realm OpenID Connect, défini comme realm par défaut.

        Args:
            realm: Nom du realm.
            issuer_url: URL de l'émetteur (realm Keycloak).
            client_id: Identifiant du client OIDC.
            client_key: Secret du client OIDC.

        Returns:
            True si le realm a été créé, False s'il existait et a été mis à jour.
        """
        params = {
            "issuer-url": issuer_url,
            "client-id": client_id,
            "client-key": client_key,
            "scopes": "email profile",
            "autocreate": 1,
            "default": 1,
        }
        if self.realm_exists(realm):
            self._request("put", f"access/domains/{realm}", **params)
            return False
        self._request(
            "post",
            "access/domains",
            realm=realm,
            type="openid",
            **{"username-claim": "preferred_username"},
            **params,
        )
        return True

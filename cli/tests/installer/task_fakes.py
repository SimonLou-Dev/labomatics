"""Faux clients et contexte pour tester les tâches d'installation sans réseau."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.proxmox_api import ProxmoxNode, VmInfo
from labomatics_cli.installer.ssh import CliKey, CommandResult, SshError
from labomatics_cli.installer.store import InstallStore
from labomatics_cli.models.install_config import InstallConfig
from labomatics_cli.tui import InstallReporter

CONFIG = {
    "proxmox": {
        "cluster_name": "lab1",
        "url": "https://pve1.lab:8006",
        "user": "root@pam",
        "token_id": "tok",
        "token_secret": "12345678-1234-1234-1234-123456789abc",
    },
    "vm": {
        "domain": "lab.fr",
        "admin_iface": "vmbr0",
        "admin_network": "192.168.50.0/24",
        "admin_gateway": "192.168.50.254",
        "vm_ip": "192.168.50.10",
        "dns_upstream": ["1.1.1.1", "9.9.9.9"],
        "ssh_keys": ["ssh-ed25519 AAAAuser user@pc"],
    },
    "vxlan": {"storage": "ceph", "zone": "labo", "mtu": 1350},
    "wan": {
        "iface": "vmbr1",
        "network": "10.210.0.0/24",
        "gateway": "10.210.0.254",
        "exclusions": ["10.210.0.1-10.210.0.5"],
    },
    "admin": {"email": "jean@lab.fr", "first_name": "Jean", "last_name": "Dupont"},
    "auth": {"directory": "local", "radius": True},
    "proxy": {"trusted_hosts": ["10.0.0.0/8"]},
    "mail": {
        "enabled": True,
        "brevo_api_key": "brevo-key",
        "from_email": "noreply@lab.fr",
        "smtp_host": "smtp.lab.fr",
        "smtp_user": "smtpuser",
        "smtp_password": "smtppw",
    },
    "nodes": {
        "pve1": {"password": "pw1"},
        "pve2": {"password": "pw2", "host": "10.0.0.12"},
    },
}


class FakeProxmox:
    """Faux `ProxmoxApi` en mémoire qui enregistre ses appels dans `calls`."""

    def __init__(self) -> None:
        """Initialise un cluster vide de deux nœuds."""
        self.calls: list[tuple] = []
        self.users: set[str] = set()
        self.tokens: set[tuple[str, str]] = set()
        self.zones: dict[str, str] = {}
        self.vm: Optional[VmInfo] = None
        self.realms: dict[str, str] = {}
        self.cloud_options: dict[str, Any] = {}
        self.dns: dict[str, dict] = {}
        self.fqdns: dict[str, list[str]] = {"pve1": ["pve1.lab.fr"]}
        self.vm_options: dict[str, Any] = {}

    def _rec(self, *call: Any) -> None:
        """Enregistre un appel.

        Args:
            *call: Nom de la méthode puis ses arguments.
        """
        self.calls.append(call)

    def names(self) -> list[str]:
        """Noms des méthodes appelées, dans l'ordre.

        Returns:
            Les noms.
        """
        return [c[0] for c in self.calls]

    def nodes(self) -> list[ProxmoxNode]:
        """Nœuds factices.

        Returns:
            Deux nœuds en ligne.
        """
        return [
            ProxmoxNode("pve1", "online", "10.0.0.11"),
            ProxmoxNode("pve2", "online", "10.0.0.12"),
        ]

    def user_exists(self, userid: str) -> bool:
        """Utilisateur existant ?

        Args:
            userid: Identifiant.

        Returns:
            True s'il a été créé.
        """
        return userid in self.users

    def create_user(
        self, userid: str, comment: str = "", email: Optional[str] = None
    ) -> None:
        """Crée un utilisateur.

        Args:
            userid: Identifiant.
            comment: Commentaire.
            email: Adresse e-mail.
        """
        self._rec("create_user", userid)
        self.users.add(userid)

    def realm_exists(self, realm: str) -> bool:
        """Realm d'authentification présent ?

        Args:
            realm: Nom du realm.

        Returns:
            True s'il a été configuré.
        """
        return realm in self.realms

    def configure_oidc_realm(
        self, realm: str, issuer_url: str, client_id: str, client_key: str
    ) -> bool:
        """Configure le realm OIDC.

        Args:
            realm: Nom du realm.
            issuer_url: Émetteur.
            client_id: Client.
            client_key: Secret du client.

        Returns:
            True si le realm vient d'être créé.
        """
        created = realm not in self.realms
        self._rec("configure_oidc_realm", realm, issuer_url, client_id, client_key)
        self.realms[realm] = issuer_url
        return created

    def grant(self, path: str, userid: str, role: str) -> None:
        """Enregistre une ACL.

        Args:
            path: Chemin.
            userid: Utilisateur.
            role: Rôle.
        """
        self._rec("grant", path, userid, role)

    def token_exists(self, userid: str, token: str) -> bool:
        """Jeton existant ?

        Args:
            userid: Utilisateur.
            token: Jeton.

        Returns:
            True s'il a été créé.
        """
        return (userid, token) in self.tokens

    def delete_token(self, userid: str, token: str) -> None:
        """Supprime un jeton.

        Args:
            userid: Utilisateur.
            token: Jeton.
        """
        self._rec("delete_token", userid, token)
        self.tokens.discard((userid, token))

    def create_token(self, userid: str, token: str) -> str:
        """Crée un jeton.

        Args:
            userid: Utilisateur.
            token: Jeton.

        Returns:
            Un secret factice.
        """
        self._rec("create_token", userid, token)
        self.tokens.add((userid, token))
        return "secret-1"

    def sdn_zone(self, zone: str) -> Optional[str]:
        """Type d'une zone.

        Args:
            zone: Nom.

        Returns:
            Le type ou None.
        """
        return self.zones.get(zone)

    def create_sdn_zone(self, zone: str, peers: list[str], mtu: int) -> None:
        """Crée une zone.

        Args:
            zone: Nom.
            peers: Pairs.
            mtu: MTU.
        """
        self._rec("create_sdn_zone", zone, peers, mtu)
        self.zones[zone] = "vxlan"

    def apply_sdn(self) -> str:
        """Applique le SDN.

        Returns:
            Un UPID factice.
        """
        self._rec("apply_sdn")
        return "UPID:pve1:sdn"

    def wait_task(self, upid: str, timeout: float = 300) -> None:
        """Enregistre l'attente d'une tâche.

        Args:
            upid: Identifiant.
            timeout: Délai.
        """
        self._rec("wait_task", upid)

    def find_vm(self, name: str) -> Optional[VmInfo]:
        """Cherche la VM.

        Args:
            name: Nom.

        Returns:
            La VM déjà créée ou None.
        """
        return self.vm

    def next_vmid(self) -> int:
        """VMID libre.

        Returns:
            105.
        """
        return 105

    def create_vm(self, node: str, vmid: int, **options: Any) -> str:
        """Crée la VM.

        Args:
            node: Nœud.
            vmid: VMID.
            **options: Options Proxmox.

        Returns:
            Un UPID factice.
        """
        self._rec("create_vm", node, vmid)
        self.vm_options = options
        self.vm = VmInfo(vmid, node, options["name"], "stopped")
        return "UPID:pve1:create"

    def attach_unused_disk(self, node: str, vmid: int, disk: str) -> None:
        """Enregistre l'attachement du disque importé.

        Args:
            node: Nœud.
            vmid: VMID.
            disk: Emplacement cible.
        """
        self._rec("attach_unused_disk", disk)

    def set_vm_config(self, node: str, vmid: int, **options: Any) -> None:
        """Enregistre la configuration cloud-init.

        Args:
            node: Nœud.
            vmid: VMID.
            **options: Options Proxmox.
        """
        self._rec("set_vm_config", vmid)
        self.cloud_options = options

    def resize_disk(self, node: str, vmid: int, disk: str, size: str) -> None:
        """Agrandit le disque.

        Args:
            node: Nœud.
            vmid: VMID.
            disk: Disque.
            size: Taille.
        """
        self._rec("resize_disk", disk, size)

    def start_vm(self, node: str, vmid: int) -> str:
        """Démarre la VM.

        Args:
            node: Nœud.
            vmid: VMID.

        Returns:
            Un UPID factice.
        """
        self._rec("start_vm", vmid)
        return "UPID:pve1:start"

    def node_dns(self, node: str) -> dict:
        """DNS d'un nœud.

        Args:
            node: Nœud.

        Returns:
            La configuration enregistrée.
        """
        return self.dns.get(node, {})

    def set_node_dns(self, node: str, dns1: str, search: str) -> None:
        """Configure le DNS d'un nœud.

        Args:
            node: Nœud.
            dns1: Serveur.
            search: Domaine.
        """
        self._rec("set_node_dns", node, dns1, search)
        self.dns[node] = {"dns1": dns1, "search": search}

    def node_fqdns(self, node: str) -> list[str]:
        """Noms ACME d'un nœud.

        Args:
            node: Nœud.

        Returns:
            Les noms configurés.
        """
        return self.fqdns.get(node, [])


class FakeSsh:
    """Fausse session SSH : mémorise commandes et fichiers, réponses par motif."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialise la session.

        Args:
            *args: Hôte et utilisateur.
            **kwargs: Options de connexion.
        """
        self.args, self.kwargs = args, kwargs
        self.commands: list[str] = []
        self.files: dict[str, str] = {}
        self.failing: dict[str, int] = {}
        self.outputs: dict[str, str] = {}
        self.connected = False
        self.closed = False

    def connect(self) -> None:
        """Simule la connexion."""
        self.connected = True

    def close(self) -> None:
        """Simule la fermeture."""
        self.closed = True

    def run(
        self, command: str, check: bool = True, timeout: int = 900
    ) -> CommandResult:
        """Simule une commande ; échoue si un motif de `failing` y figure.

        Args:
            command: Commande.
            check: Lève une erreur en cas d'échec.
            timeout: Délai (ignoré).

        Returns:
            Le résultat simulé.

        Raises:
            SshError: Si `check` est vrai et que la commande échoue.
        """
        self.commands.append(command)
        code = next((c for p, c in self.failing.items() if p in command), 0)
        out = next((o for p, o in self.outputs.items() if p in command), None)
        explicit = out is not None
        if out is None:
            out = "Docker version 27\n"
        result = CommandResult(out if code == 0 or explicit else "", "", code)
        if check and not result.ok:
            raise SshError("échec")
        return result

    def put_text(self, path: str, content: str, mode: int = 0o644) -> None:
        """Mémorise un fichier.

        Args:
            path: Chemin.
            content: Contenu.
            mode: Permissions (ignorées).
        """
        self.files[path] = content


def make_ctx(
    tmp_path: Path,
    api: Optional[FakeProxmox] = None,
    sessions: Optional[list[FakeSsh]] = None,
    failing: Optional[dict[str, int]] = None,
    outputs: Optional[dict[str, str]] = None,
    config: Optional[dict] = None,
    keycloak: Optional[Any] = None,
) -> InstallContext:
    """Construit un contexte d'installation entièrement factice.

    Args:
        tmp_path: Dossier temporaire (store et clé SSH).
        api: Faux Proxmox à utiliser.
        sessions: Liste qui reçoit les fausses sessions SSH créées.
        failing: Motifs de commande SSH qui échouent (motif -> code), pour chaque session.
        outputs: Sorties SSH par motif de commande, pour chaque session.
        config: Configuration complète à utiliser à la place de `CONFIG`.
        keycloak: Faux client Keycloak.

    Returns:
        Le contexte.
    """
    store = InstallStore.open("lab1", tmp_path / "clusters")
    store.save_config(InstallConfig.model_validate(config or CONFIG))
    fake = api or FakeProxmox()
    created = sessions if sessions is not None else []

    def ssh_factory(*args: Any, **kwargs: Any) -> FakeSsh:
        """Crée et mémorise une fausse session.

        Args:
            *args: Hôte et utilisateur.
            **kwargs: Options de connexion.

        Returns:
            La session.
        """
        session = FakeSsh(*args, **kwargs)
        session.failing.update(failing or {})
        session.outputs.update(outputs or {})
        created.append(session)
        return session

    ctx = InstallContext(
        store.config,
        store,
        InstallReporter(["étape"]),
        api_factory=lambda *a: fake,
        ssh_factory=ssh_factory,
        keycloak_factory=lambda *a, **k: keycloak,
        key=CliKey(tmp_path / "ssh" / "labomatics-cli"),
    )
    return ctx

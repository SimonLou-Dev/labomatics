import pytest
import requests
from proxmoxer.core import ResourceException

from installer_fakes import FakeClientFactory
from labomatics_cli.installer.proxmox_api import (
    ProxmoxApi,
    ProxmoxAuthError,
    ProxmoxConnectionError,
    ProxmoxError,
    ProxmoxPermissionError,
)


def make(factory=None, url="https://pve1.lab:8443"):
    """Crée une API branchée sur un faux client."""
    factory = factory or FakeClientFactory()
    return ProxmoxApi(url, "root@pam", "tok", "secret", client_factory=factory), factory


def test_keeps_port_and_disables_tls_verification():
    """Le port de l'URL est conservé et la vérification TLS désactivée."""
    _, factory = make()
    args, kwargs = factory.calls[0]
    assert args == ("pve1.lab",) and kwargs["port"] == 8443
    assert kwargs["verify_ssl"] is False and kwargs["timeout"] == 10
    assert kwargs["token_name"] == "tok" and kwargs["token_value"] == "secret"


def test_default_port():
    """Sans port dans l'URL, 8006 est utilisé."""
    _, factory = make(url="https://pve1.lab")
    assert factory.calls[0][1]["port"] == 8006


def test_version_cluster_name_and_nodes():
    """Version, nom du cluster et nœuds avec leur IP."""
    api, _ = make()
    assert api.version() == "8.2.4"
    assert api.cluster_name() == "pvecl"
    assert [(n.name, n.ip, n.online) for n in api.nodes()] == [
        ("pve1", "10.0.0.11", True),
        ("pve2", "10.0.0.12", True),
    ]


def test_cluster_name_none_when_standalone_and_single_node_ip():
    """Nœud isolé : pas de nom de cluster, IP = hôte de l'URL."""
    factory = FakeClientFactory()
    factory.data["cluster/status"] = [{"type": "node", "name": "solo"}]
    factory.data["nodes"] = [{"node": "solo", "status": "online"}]
    api, _ = make(factory)
    assert api.cluster_name() is None
    assert api.nodes()[0].ip == "pve1.lab"


def test_permissions_and_missing_privileges():
    """Les privilèges d'administration manquants sont listés."""
    api, factory = make()
    assert api.missing_privileges() == []
    factory.data["access/permissions"] = {"/": {"Sys.Modify": 1}}
    assert "VM.Allocate" in api.missing_privileges()
    factory.data["access/permissions"] = {}
    assert len(api.missing_privileges()) == 5


def test_bridges_and_common_bridges_labels():
    """Seuls les bridges communs sont proposés, avec CIDR éventuel."""
    api, _ = make()
    assert [b.name for b in api.bridges("pve1")] == ["vmbr0", "vmbr1"]
    common = api.common_bridges()
    assert [b.label for b in common] == ["vmbr0 (10.100.25.1/24)"]
    assert common[0].gateway == "10.100.25.254"
    api._client._data["nodes/pve1/network"][0].pop("cidr")
    assert api.common_bridges()[0].label == "vmbr0 (sans IP)"


def test_shared_storages_filters():
    """Stockage partagé, contenu images, présent sur tous les nœuds."""
    api, _ = make()
    assert [s.name for s in api.shared_storages()] == ["ceph"]


def test_sdn_zone():
    """Type de la zone, ou None si elle n'existe pas."""
    api, _ = make()
    assert api.sdn_zone("labo") == "vxlan"
    assert api.sdn_zone("x") == "evpn"
    assert api.sdn_zone("autre") is None


@pytest.mark.parametrize(
    "error, expected, text",
    [
        (ResourceException(401, "Unauthorized", ""), ProxmoxAuthError, "401"),
        (ResourceException(403, "Forbidden", ""), ProxmoxPermissionError, "403"),
        (ResourceException(500, "Boom", ""), ProxmoxError, "500"),
        (requests.exceptions.SSLError("bad cert"), ProxmoxConnectionError, "TLS"),
        (
            requests.exceptions.ConnectionError("down"),
            ProxmoxConnectionError,
            "joindre",
        ),
        (requests.exceptions.Timeout(), ProxmoxConnectionError, "Délai"),
    ],
)
def test_errors_are_translated(error, expected, text):
    """Les erreurs HTTP, TLS et réseau deviennent des exceptions françaises."""
    factory = FakeClientFactory()
    factory.data["version"] = error
    api, _ = make(factory)
    with pytest.raises(expected) as info:
        api.version()
    assert text in str(info.value)


class RecordingClient:
    """Faux client proxmoxer qui enregistre les verbes et chemins appelés."""

    def __init__(self, responses, calls, path=""):
        """Initialise la ressource.

        Args:
            responses: Réponses par (verbe, chemin).
            calls: Liste partagée recevant (verbe, chemin, paramètres).
            path: Chemin accumulé.
        """
        self._responses, self._calls, self._path = responses, calls, path

    def __getattr__(self, name):
        """Descend d'un niveau ou renvoie un verbe HTTP.

        Args:
            name: Segment de chemin ou verbe.

        Returns:
            La sous-ressource ou la fonction du verbe.
        """
        if name in ("get", "post", "put", "delete"):

            def call(**params):
                """Enregistre l'appel et renvoie la réponse programmée."""
                self._calls.append((name, self._path, params))
                return self._responses.get((name, self._path))

            return call
        return RecordingClient(
            self._responses, self._calls, f"{self._path}/{name}".strip("/")
        )


def recording(responses=None):
    """Crée une API branchée sur un client enregistreur."""
    calls = []
    api = ProxmoxApi(
        "https://pve1:8006",
        "root@pam",
        "t",
        "s",
        poll_interval=0,
        client_factory=lambda *a, **k: RecordingClient(responses or {}, calls),
    )
    return api, calls


def test_token_user_and_acl_calls():
    """Utilisateur, jeton sans privsep et ACL utilisent les bons verbes et chemins."""
    api, calls = recording(
        {
            ("get", "access/users"): [{"userid": "labomatics@pve"}],
            ("get", "access/users/labomatics@pve/token"): [{"tokenid": "labomatics"}],
            ("post", "access/users/labomatics@pve/token/labomatics"): {"value": "sec"},
        }
    )
    assert api.user_exists("labomatics@pve") and not api.user_exists("x@pve")
    assert api.token_exists("labomatics@pve", "labomatics")
    assert not api.token_exists("labomatics@pve", "autre")
    assert api.create_token("labomatics@pve", "labomatics") == "sec"
    api.delete_token("labomatics@pve", "labomatics")
    api.grant("/", "labomatics@pve", "Administrator")
    assert calls[-3] == (
        "post",
        "access/users/labomatics@pve/token/labomatics",
        {"privsep": 0},
    )
    assert calls[-2][:2] == ("delete", "access/users/labomatics@pve/token/labomatics")
    assert calls[-1] == (
        "put",
        "access/acl",
        {
            "path": "/",
            "users": "labomatics@pve",
            "roles": "Administrator",
            "propagate": 1,
        },
    )


def test_sdn_zone_creation_and_apply():
    """La zone VXLAN est créée avec ses pairs, le SDN appliqué renvoie l'UPID."""
    api, calls = recording({("put", "cluster/sdn"): "UPID:pve1:x"})
    api.create_sdn_zone("labo", ["10.0.0.1", "10.0.0.2"], 1350)
    assert calls[0] == (
        "post",
        "cluster/sdn/zones",
        {"zone": "labo", "type": "vxlan", "peers": "10.0.0.1,10.0.0.2", "mtu": 1350},
    )
    assert api.apply_sdn() == "UPID:pve1:x"


def test_wait_task_success_failure_and_timeout():
    """L'attente suit la tâche, signale l'échec et le dépassement du délai."""
    path = "nodes/pve1/tasks/UPID:pve1:x/status"
    api, _ = recording({("get", path): {"status": "stopped", "exitstatus": "OK"}})
    api.wait_task("UPID:pve1:x")
    api, _ = recording({("get", path): {"status": "stopped", "exitstatus": "boom"}})
    with pytest.raises(ProxmoxError, match="boom"):
        api.wait_task("UPID:pve1:x")
    api, _ = recording({("get", path): {"status": "running"}})
    with pytest.raises(ProxmoxError, match="Délai"):
        api.wait_task("UPID:pve1:x", timeout=0)


def test_vm_and_image_calls():
    """Recherche de VM, image « import », création, démarrage et DNS des nœuds."""
    api, calls = recording(
        {
            ("get", "cluster/resources"): [
                {"vmid": 100, "node": "pve2", "name": "labomatics", "status": "running"}
            ],
            ("get", "cluster/nextid"): "101",
            ("get", "nodes/pve1/config"): {
                "acmedomain0": "domain=a.lab.fr,plugin=x",
                "acmedomain1": "b.lab.fr",
            },
            ("post", "nodes/pve1/qemu"): "UPID:pve1:c",
        }
    )
    vm = api.find_vm("labomatics")
    assert (vm.vmid, vm.node, vm.status) == (100, "pve2", "running")
    assert api.find_vm("absente") is None
    assert api.next_vmid() == 101
    assert api.node_fqdns("pve1") == ["a.lab.fr", "b.lab.fr"]
    assert api.create_vm("pve1", 101, name="x") == "UPID:pve1:c"
    assert calls[-1] == ("post", "nodes/pve1/qemu", {"vmid": 101, "name": "x"})
    api.set_node_dns("pve1", "10.0.0.5", "lab.fr")
    assert calls[-1] == (
        "put",
        "nodes/pve1/dns",
        {"dns1": "10.0.0.5", "search": "lab.fr"},
    )

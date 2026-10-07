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

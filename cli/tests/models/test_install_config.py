from labomatics_cli.models.install_config import (
    AdminSection,
    DirectoryMode,
    InstallConfig,
)

PROXMOX = {
    "proxmox.cluster_name": "pve",
    "proxmox.url": "https://pve:8006",
    "proxmox.user": "root@pam",
    "proxmox.token_id": "t",
    "proxmox.token_secret": "s",
}


def test_flat_round_trip_with_nodes_and_lists():
    """Vérifie l'aller-retour plat ↔ config avec nœuds et listes."""
    values = {
        **PROXMOX,
        "vm.domain": "lab.local",
        "vm.admin_iface": "vmbr0",
        "vm.admin_network": "10.0.0.0/24",
        "vm.admin_gateway": "10.0.0.1",
        "vm.vm_ip": "10.0.0.5",
        "vm.dns_upstream": ["1.1.1.1", "9.9.9.9"],
        "nodes.pve1.user": "root",
        "nodes.pve1.password": "pw1",
        "nodes.pve2.password": "pw2",
    }
    cfg = InstallConfig().merge_flat(values)
    flat = cfg.to_flat()
    assert flat["vm.dns_upstream"] == ["1.1.1.1", "9.9.9.9"]
    assert flat["vm.memory"] == 8192
    assert flat["nodes.pve2.user"] == "root"
    assert InstallConfig().merge_flat(flat).to_flat() == flat


def test_partial_section_ignored_until_complete():
    """Vérifie qu'une section incomplète est ignorée puis fusionnée une fois complète."""
    cfg = InstallConfig().merge_flat({"proxmox.url": "https://x"})
    assert cfg.proxmox is None
    cfg = cfg.merge_flat(PROXMOX)
    assert cfg.proxmox is not None
    cfg = cfg.merge_flat({"proxmox.url": "https://y"})
    assert cfg.proxmox.url == "https://y"
    assert cfg.proxmox.user == "root@pam"


def test_section_filter_and_unknown_keys():
    """Vérifie le filtre par section et l'ignorance des clés inconnues."""
    values = {**PROXMOX, "auth.radius": True, "bogus.key": 1, "nope": 2}
    cfg = InstallConfig().merge_flat(values, section="auth")
    assert cfg.proxmox is None
    assert cfg.auth.radius is True
    assert cfg.auth.directory == DirectoryMode.local


def test_locked_keys():
    """Vérifie que les clés verrouillées sont celles déjà renseignées."""
    assert InstallConfig().locked_keys() == set()
    cfg = InstallConfig().merge_flat(PROXMOX)
    assert cfg.locked_keys() == set(PROXMOX)


def test_username():
    """Vérifie le calcul de l'identifiant prenom.nom sans accents."""
    admin = AdminSection(email="a@b.c", first_name="Éloïse Marie", last_name="Dupont")
    assert admin.username == "eloise-marie.dupont"


def test_logical_names_default_to_cluster_name():
    """Vérifie que les noms WAN et VNet prennent le nom du cluster par défaut."""
    values = {
        **PROXMOX,
        "wan.iface": "vmbr1",
        "wan.network": "172.16.0.0/24",
        "wan.gateway": "172.16.0.254",
        "vxlan.storage": "ceph",
    }
    cfg = InstallConfig().merge_flat(values)
    assert cfg.wan.name == "pve"
    assert cfg.vxlan.vnet_name == "pve"
    custom = cfg.merge_flat({"wan.name": "esgilabs"})
    assert custom.wan.name == "esgilabs"


def test_schema_version_and_new_fields():
    """Vérifie la version de schéma et les champs ajoutés (fuseau, VNI, hôte)."""
    values = {
        "nodes.pve1.password": "pw",
        "nodes.pve1.host": "10.0.0.11",
        **PROXMOX,
        "vxlan.storage": "ceph",
        "vxlan.vni_exclusions": ["100", "200-210"],
    }
    cfg = InstallConfig().merge_flat(values)
    assert cfg.version == 1
    assert cfg.nodes["pve1"].host == "10.0.0.11"
    assert cfg.vxlan.vni_exclusions == ["100", "200-210"]
    assert "version" not in cfg.to_flat()

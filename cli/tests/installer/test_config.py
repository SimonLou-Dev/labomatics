from labomatics_cli.installer.config import (
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
    cfg = InstallConfig().merge_flat({"proxmox.url": "https://x"})
    assert cfg.proxmox is None
    cfg = cfg.merge_flat(PROXMOX)
    assert cfg.proxmox is not None
    cfg = cfg.merge_flat({"proxmox.url": "https://y"})
    assert cfg.proxmox.url == "https://y"
    assert cfg.proxmox.user == "root@pam"


def test_section_filter_and_unknown_keys():
    values = {**PROXMOX, "auth.radius": True, "bogus.key": 1, "nope": 2}
    cfg = InstallConfig().merge_flat(values, section="auth")
    assert cfg.proxmox is None
    assert cfg.auth.radius is True
    assert cfg.auth.directory == DirectoryMode.local


def test_locked_keys():
    assert InstallConfig().locked_keys() == set()
    cfg = InstallConfig().merge_flat(PROXMOX)
    assert cfg.locked_keys() == set(PROXMOX)


def test_username():
    admin = AdminSection(email="a@b.c", first_name="Éloïse Marie", last_name="Dupont")
    assert admin.username == "eloise-marie.dupont"

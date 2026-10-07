from labomatics_cli.installer.proxmox_api import VmInfo
from labomatics_cli.installer.tasks.dns import DnsTask
from labomatics_cli.installer.tasks.docker import DockerTask
from labomatics_cli.installer.tasks.node_dns import NodeDnsTask
from labomatics_cli.installer.tasks.sdn import SdnTask
from labomatics_cli.installer.tasks.token import TokenTask
from labomatics_cli.installer.tasks.vm import VmTask
from task_fakes import FakeProxmox, make_ctx
import pytest


def test_token_creates_user_acl_and_saves_secret(tmp_path):
    """Chemin création : utilisateur, ACL, jeton et secret sauvegardé."""
    api = FakeProxmox()
    ctx = make_ctx(tmp_path, api)
    TokenTask().run(ctx)
    assert api.names() == ["create_user", "grant", "create_token"]
    assert ("grant", "/", "labomatics@pve", "Administrator") in api.calls
    assert ctx.store.secrets.labomatics_token_secret == "secret-1"


def test_token_idempotent_and_recreated_when_secret_lost(tmp_path):
    """Jeton connu : rien ; jeton au secret perdu : supprimé puis recréé."""
    api = FakeProxmox()
    ctx = make_ctx(tmp_path, api)
    TokenTask().run(ctx)
    api.calls.clear()
    TokenTask().run(ctx)
    assert "create_token" not in api.names() and "delete_token" not in api.names()
    ctx.store.save_secret("labomatics_token_secret", "")
    api.calls.clear()
    TokenTask().run(ctx)
    assert api.names() == ["grant", "delete_token", "create_token"]
    assert ctx.store.secrets.labomatics_token_secret == "secret-1"


def test_sdn_creates_zone_with_node_ips_then_skips(tmp_path):
    """Zone absente : créée avec les IP des nœuds ; présente en vxlan : ignorée."""
    api = FakeProxmox()
    ctx = make_ctx(tmp_path, api)
    task = SdnTask()
    assert task.is_needed(ctx)
    task.run(ctx)
    assert ("create_sdn_zone", "labo", ["10.0.0.11", "10.0.0.12"], 1350) in api.calls
    assert "apply_sdn" in api.names()
    assert not task.is_needed(ctx)


def test_sdn_refuses_other_zone_type(tmp_path):
    """Une zone du même nom d'un autre type est une erreur."""
    api = FakeProxmox()
    api.zones["labo"] = "evpn"
    with pytest.raises(RuntimeError, match="evpn"):
        SdnTask().is_needed(make_ctx(tmp_path, api))


def test_vm_creation_path(tmp_path):
    """Image absente : téléchargée sur le nœud, disque importé, attaché, cloud-init, SSH."""
    api, sessions = FakeProxmox(), []
    ctx = make_ctx(
        tmp_path, api, sessions, failing={"test -f": 1}, outputs={"lsblk": "sda\n"}
    )
    VmTask().run(ctx)
    assert api.names() == [
        "create_vm",
        "wait_task",
        "attach_unused_disk",
        "resize_disk",
        "set_vm_config",
        "start_vm",
        "wait_task",
    ]
    node_ssh = sessions[0]
    assert node_ssh.args == ("pve1", "root")
    assert any("wget -nv" in c and ".part" in c for c in node_ssh.commands)
    assert any(
        "qm importdisk 105" in c and "ceph --format qcow2" in c
        for c in node_ssh.commands
    )
    hardware = api.vm_options
    assert (
        hardware["net0"] == "virtio,bridge=vmbr0" and hardware["agent"] == "enabled=1"
    )
    assert "scsi0" not in hardware and "import-from" not in str(hardware)
    opts = api.cloud_options
    assert opts["ipconfig0"] == "ip=192.168.50.10/24,gw=192.168.50.254"
    assert opts["nameserver"] == "1.1.1.1 9.9.9.9"
    assert (
        "ssh-ed25519%20AAAAuser" in opts["sshkeys"]
        and "labomatics-cli" in opts["sshkeys"]
    )
    assert opts["cipassword"] == ctx.store.secrets.vm_password
    assert ctx.store.get_data("vmid") == 105 and ctx.store.get_data("vm_node") == "pve1"
    assert sessions[1].args == ("192.168.50.10", "labomatics") and sessions[1].connected
    assert "sudo growpart /dev/sda 3" in sessions[1].commands
    assert sessions[1].commands[-1] == "sudo btrfs filesystem resize max /"


def test_vm_existing_is_reused(tmp_path):
    """VM existante : aucune création, démarrage seulement si elle est arrêtée."""
    api = FakeProxmox()
    api.vm = VmInfo(120, "pve2", "labomatics", "running")
    ctx = make_ctx(tmp_path, api)
    VmTask().run(ctx)
    assert api.calls == []
    assert ctx.store.get_data("vmid") == 120 and ctx.store.get_data("vm_node") == "pve2"
    api.vm = VmInfo(120, "pve2", "labomatics", "stopped")
    VmTask().run(make_ctx(tmp_path, api))
    assert api.names() == ["start_vm", "wait_task"]


def test_vm_image_already_on_node_is_not_downloaded(tmp_path):
    """Image déjà dans le cache du nœud : pas de téléchargement."""
    sessions = []
    VmTask().run(make_ctx(tmp_path, FakeProxmox(), sessions))
    assert not any("wget" in c for c in sessions[0].commands)
    assert any("qm importdisk" in c for c in sessions[0].commands)


def test_docker_installs_only_when_absent(tmp_path):
    """Docker absent : script d'installation ; présent : tâche ignorée."""
    sessions = []
    ctx = make_ctx(tmp_path, sessions=sessions)
    task = DockerTask()
    assert not task.is_needed(ctx)
    sessions[0].failing["docker --version"] = 127
    assert task.is_needed(ctx)
    sessions[0].failing.clear()
    task.run(ctx)
    assert "docker-ce" in sessions[0].commands[-1]


def test_dns_writes_config_and_restarts(tmp_path):
    """dnsmasq : fichier rendu (enregistrements, amont, nœuds) puis script appliqué."""
    sessions = []
    ctx = make_ctx(tmp_path, sessions=sessions)
    DnsTask().run(ctx)
    ssh = sessions[0]
    conf = ssh.files["/tmp/labomatics-dnsmasq.conf"]
    assert "address=/keycloak.lab.fr/192.168.50.10" in conf
    assert "address=/traefik.lab.fr/192.168.50.10" in conf
    assert "address=/api.labomatics.lab.fr/192.168.50.10" in conf
    assert "server=1.1.1.1" in conf and "server=9.9.9.9" in conf
    assert "address=/pve1.lab.fr/10.0.0.11" in conf
    assert (
        ssh.files["/tmp/labomatics-resolv.conf"]
        == "nameserver 127.0.0.1\nsearch lab.fr\n"
    )
    assert ssh.files["/tmp/labomatics-nm-no-dns.conf"] == "[main]\ndns=none\n"
    script = ssh.commands[-1]
    assert "no-dns-update.conf" in script and "reload NetworkManager" in script
    order = [
        "dnf install -y dnsmasq",
        "disable --now systemd-resolved",
        "/etc/resolv.conf",
        "enable dnsmasq",
    ]
    positions = [script.index(item) for item in order]
    assert positions == sorted(positions)


def test_node_dns_sets_then_is_idempotent(tmp_path):
    """DNS des nœuds : appliqué une fois, puis plus rien à faire."""
    api = FakeProxmox()
    ctx = make_ctx(tmp_path, api)
    NodeDnsTask().run(ctx)
    assert api.names() == ["set_node_dns", "set_node_dns"]
    assert ("set_node_dns", "pve1", "192.168.50.10", "lab.fr") in api.calls
    api.calls.clear()
    NodeDnsTask().run(ctx)
    assert api.calls == []


def test_vm_growpart_nochange_is_tolerated_other_errors_are_not(tmp_path):
    """NOCHANGE de growpart est toléré ; une autre erreur fait échouer."""
    sessions = []
    ctx = make_ctx(tmp_path, FakeProxmox(), sessions, outputs={"lsblk": "sda\n"})
    ctx.vm_ssh.failing["growpart"] = 1
    ctx.vm_ssh.outputs["growpart"] = "NOCHANGE: partition 3 is size 1"
    VmTask()._grow_filesystem(ctx)
    assert ctx.vm_ssh.commands[-1].startswith("sudo btrfs")
    ctx.vm_ssh.outputs["growpart"] = "boum"
    with pytest.raises(Exception, match="growpart"):
        VmTask()._grow_filesystem(ctx)

import os
import re
import stat

import pytest

from labomatics_cli.installer.secrets import InstallSecrets, PasswordGenerator
from labomatics_cli.installer.store import InstallMode, InstallStore, InstallStatus

PROXMOX = {
    "proxmox.cluster_name": "pve",
    "proxmox.url": "https://pve:8006",
    "proxmox.user": "root@pam",
    "proxmox.token_id": "t",
    "proxmox.token_secret": "s",
}


def mode_of(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_persistence_across_reopen(tmp_path):
    store = InstallStore.open("pve", tmp_path)
    store.save_page(PROXMOX, "proxmox")
    store.mark_in_progress()
    store.mark_task_done("a")
    store.mark_task_done("b")
    store.mark_task_done("a")
    store.set_data("vmid", 100)
    store.save_secret("keycloak_client_secret", "xyz")
    again = InstallStore.open("pve", tmp_path)
    assert again.config.proxmox.url == "https://pve:8006"
    assert again.completed_tasks == ["a", "b"]
    assert again.is_task_done("b")
    assert again.get_data("vmid") == 100
    assert again.secrets.keycloak_client_secret == "xyz"
    assert again.status == InstallStatus.in_progress


def test_permissions_and_no_tmp_left(tmp_path):
    store = InstallStore.open("pve", tmp_path)
    store.save_page(PROXMOX, "proxmox")
    store.mark_in_progress()
    assert mode_of(store.directory) == 0o700
    assert mode_of(store.directory / "install.yaml") == 0o600
    assert mode_of(store.directory / "state.json") == 0o600
    assert sorted(p.name for p in store.directory.iterdir()) == [
        "install.yaml",
        "state.json",
    ]


def test_secrets_never_regenerated(tmp_path):
    store = InstallStore.open("pve", tmp_path)
    first = store.secrets
    assert first.encryption_key
    assert first.pg_root_password
    second = InstallStore.open("pve", tmp_path).secrets
    assert second == first
    assert first.ensure(PasswordGenerator()) == first


def test_save_secret_unknown(tmp_path):
    with pytest.raises(KeyError):
        InstallStore.open("pve", tmp_path).save_secret("nope", "x")


def test_mode_derivation(tmp_path):
    store = InstallStore.open("pve", tmp_path)
    assert store.mode == InstallMode.new
    store.mark_in_progress()
    assert store.mode == InstallMode.resume
    store.mark_failed("boom")
    assert store.mode == InstallMode.resume
    assert store.last_error == "boom"
    assert not store.is_installed
    store.mark_completed()
    assert store.mode == InstallMode.edit
    assert InstallStore.open("pve", tmp_path).is_installed


def test_mode_resume_when_pages_saved_before_install(tmp_path):
    store = InstallStore.open("pve", tmp_path)
    store.save_page({"admin.email": "a@b.fr", "admin.first_name": "A"}, "admin")
    assert store.mode == InstallMode.new
    store.save_page({"admin.last_name": "B"}, "admin")
    assert store.mode == InstallMode.resume


def test_list_clusters(tmp_path):
    assert InstallStore.list_clusters(tmp_path) == []
    InstallStore.open("b", tmp_path).mark_in_progress()
    InstallStore.open("a", tmp_path).save_page(PROXMOX)
    assert InstallStore.list_clusters(tmp_path) == ["a", "b"]


def test_password_policy():
    gen = PasswordGenerator()
    forbidden = set("\"'\\$`#= \n")
    for _ in range(1000):
        pw = gen.generate()
        assert len(pw) >= 16
        assert len(re.findall(r"[A-Z]", pw)) >= 2
        assert len(re.findall(r"[0-9]", pw)) >= 2
        assert len(re.findall(r"[a-z]", pw)) >= 3
        assert len(re.findall(r"[^A-Za-z0-9]", pw)) >= 2
        assert not forbidden & set(pw)
        assert pw[0].isalnum()


def test_ensure_fills_only_missing():
    secrets = InstallSecrets(pg_root_password="keep").ensure(PasswordGenerator())
    assert secrets.pg_root_password == "keep"
    assert secrets.admin_temp_password

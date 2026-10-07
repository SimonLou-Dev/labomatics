import asyncio

from installer_fakes import UUID, FakeApi, fake_checks
from labomatics_cli.installer.app import InstallerApp
from labomatics_cli.installer.pages import NEW_CLUSTER, ClusterChoice
from labomatics_cli.installer.proxmox_api import ProxmoxConnectionError
from labomatics_cli.installer.store import InstallMode, InstallStore
from labomatics_cli.installer.tasks import INSTALL_TASKS, PlaceholderRunner
from labomatics_cli.models.install_config import InstallConfig
from labomatics_cli.tui import InstallReporter
from tui_harness import CTRL_C, DOWN, ENTER, TAB, WaitUntil, check, run

PROXMOX = {
    "cluster_name": "lab1",
    "url": "https://pve1.lab:8006",
    "user": "root@pam",
    "token_id": "tok",
    "token_secret": UUID,
}
VM = {
    "domain": "lab.fr",
    "admin_iface": "vmbr0",
    "admin_network": "192.168.50.0/24",
    "admin_gateway": "192.168.50.254",
    "vm_ip": "192.168.50.10",
    "dns_upstream": ["1.1.1.1"],
}


def make_app(tmp_path, cluster=None, api=None, **kw):
    """Crée une application avec un faux Proxmox et un dossier temporaire."""
    return InstallerApp(
        cluster,
        base_dir=tmp_path,
        api_factory=kw.pop("api_factory", lambda *a: api or FakeApi()),
        checks=fake_checks(("192.168.50.254",)),
        **kw,
    )


def seed(tmp_path, **sections):
    """Crée un cluster sauvegardé avec les sections données."""
    store = InstallStore.open("lab1", tmp_path)
    store.save_config(InstallConfig.model_validate(sections))
    return store


def test_placeholder_runner_skips_the_13_tasks(tmp_path):
    """Le runner provisoire ignore les 13 tâches."""
    assert len(INSTALL_TASKS) == 13 and INSTALL_TASKS[7] == "Propagation des CA"
    reporter = InstallReporter(list(INSTALL_TASKS))
    store = InstallStore.open("x", tmp_path)
    asyncio.run(PlaceholderRunner().run(store, {}, reporter))
    assert set(reporter.status) == {"skipped"}


def test_new_mode_prefills_name_and_refuses_existing(tmp_path):
    """Nouveau cluster : nom prérempli, nom déjà pris refusé."""
    app = make_app(tmp_path, "lab2")
    assert app._select_cluster() and app.store is None
    w = app.build_wizard()
    name = w.steps[0].fields[0]
    assert name.value == "lab2" and not name.locked
    seed(tmp_path, proxmox=PROXMOX)
    name.set_value("lab1")
    assert not name.validate() and "existe déjà" in name.error


def test_page_save_opens_store_and_locks_name(tmp_path):
    """La sauvegarde de la page 1 ouvre le store, enregistre sa section seule et verrouille le nom."""
    app = make_app(tmp_path)
    w = app.build_wizard()
    step = w.steps[0]
    for key, value in {f"proxmox.{k}": v for k, v in PROXMOX.items()}.items():
        next(f for f in step.fields if f.key == key).set_value(value)
    w.collect()
    app._save(step, w.ctx)
    assert app.store is not None and InstallStore.list_clusters(tmp_path) == ["lab1"]
    assert app.store.config.proxmox.url == "https://pve1.lab:8006"
    assert app.store.config.vm is None
    assert step.fields[0].locked
    assert app.mode == InstallMode.resume


def test_resume_starts_at_first_unsaved_page(tmp_path):
    """Reprise : préremplissage, rien de verrouillé sauf le nom, départ à la 3e page."""
    seed(tmp_path, proxmox=PROXMOX, vm=VM)
    app = make_app(tmp_path, "lab1")
    app._select_cluster()
    assert app.mode == InstallMode.resume
    w = app.build_wizard()
    assert w.index == 2 and w.current.title == "Labs : WAN"
    assert w.ctx.data["api"] is not None
    vm_fields = {f.key: f for f in w.steps[1].fields}
    assert (
        vm_fields["vm.domain"].value == "lab.fr" and not vm_fields["vm.domain"].locked
    )
    assert w.steps[0].fields[0].locked


def test_resume_restarts_at_first_page_when_proxmox_is_down(tmp_path):
    """Reprise : si Proxmox est injoignable, on repart de la première page."""

    def down(*args):
        """Simule un Proxmox injoignable."""
        raise ProxmoxConnectionError("injoignable")

    seed(tmp_path, proxmox=PROXMOX, vm=VM)
    app = make_app(tmp_path, "lab1", api_factory=down)
    app._select_cluster()
    assert app.build_wizard().index == 0


def test_edit_mode_locks_saved_values(tmp_path):
    """Édition : tout ce qui est en config est verrouillé, le reste reste libre."""
    store = seed(tmp_path, proxmox=PROXMOX, vm=VM)
    store.mark_completed()
    app = make_app(tmp_path, "lab1")
    app._select_cluster()
    assert app.mode == InstallMode.edit
    w = app.build_wizard()
    assert w.index == 0
    by_key = {f.key: f for s in w.steps for f in s.fields}
    assert by_key["vm.domain"].locked and by_key["proxmox.url"].locked
    assert not by_key["wan.network"].locked
    assert by_key["vm.domain"].value == "lab.fr"


def test_select_cluster_uses_choice_when_clusters_exist(tmp_path, monkeypatch):
    """Sans --cluster et avec des clusters existants, le choix est proposé."""
    seed(tmp_path, proxmox=PROXMOX)
    monkeypatch.setattr(ClusterChoice, "ask", lambda self: "lab1")
    app = make_app(tmp_path)
    assert app._select_cluster() and app.store is not None
    monkeypatch.setattr(ClusterChoice, "ask", lambda self: NEW_CLUSTER)
    app = make_app(tmp_path)
    assert app._select_cluster() and app.store is None and app.cluster is None
    monkeypatch.setattr(ClusterChoice, "ask", lambda self: None)
    assert not make_app(tmp_path)._select_cluster()


def test_cluster_choice_screen():
    """L'écran de choix renvoie le cluster sélectionné."""
    wizard = ClusterChoice(["lab1", "lab2"]).build_wizard()
    result, _ = run(wizard, [ENTER, DOWN, DOWN, ENTER, TAB, ENTER])
    assert result == {"cluster": "lab2"}


def test_first_page_flow_saves_and_advances(tmp_path):
    """Page Proxmox saisie au clavier : connexion simulée, sauvegarde, passage à la page VM."""
    app = make_app(tmp_path)
    w = app.build_wizard()
    feed = [
        TAB,
        "https://pve1.lab:8006",
        TAB,
        TAB,
        "tok",
        TAB,
        UUID,
        TAB,
        ENTER,
        WaitUntil(lambda: w.index == 1),
        check(
            lambda: app.store is not None
            and app.store.config.proxmox.token_id == "tok"
            and w.ctx.data["nodes"],
            "page sauvegardée",
        ),
        CTRL_C,
    ]
    result, _ = run(w, feed)
    assert result is None

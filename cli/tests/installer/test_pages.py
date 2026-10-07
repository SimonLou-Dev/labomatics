import asyncio


from installer_fakes import UUID, FakeApi, fake_checks
from labomatics_cli.installer.pages import (
    PAGE_CLASSES,
    PAGE_SECTIONS,
    AdminPage,
    AuthPage,
    LdapPage,
    MailPage,
    NodesPage,
    ProxmoxPage,
    ProxyPage,
    VmPage,
    VxlanPage,
    WanPage,
)
from labomatics_cli.installer.pages.rules import AddressPool
from labomatics_cli.installer.proxmox_api import Bridge, ProxmoxNode
from labomatics_cli.models.install_config import InstallConfig
from labomatics_cli.tui import Wizard, WizardContext


def make(page, data=None, values=None, others=()):
    """Construit un Wizard (non lancé) : la page testée en premier, puis ses voisines."""
    ctx = WizardContext(data=dict(data or {}))
    steps = [page.build()] + [p.build() for p in others]
    steps[0].visible_if = None
    wizard = Wizard("T", steps, recap=False, context=ctx)
    fill(wizard, values or {})
    return wizard


def fill(wizard, values):
    """Renseigne des champs par clé puis recalcule les valeurs."""
    fields = {f.key: f for s in wizard.steps for f in s.fields}
    for key, value in values.items():
        fields[key].set_value(value)
    wizard.collect()


def field(wizard, key):
    """Champ d'un wizard par sa clé."""
    return next(f for s in wizard.steps for f in s.fields if f.key == key)


def submit(wizard):
    """Valide l'étape puis lance son on_submit ; renvoie (valide, erreur)."""
    step = wizard.steps[0]
    if not step.validate():
        return False, None
    if step.on_submit is None:
        return True, None
    return True, asyncio.run(step.on_submit(wizard.ctx))


NETWORK_DATA = {
    "bridges": [Bridge("vmbr0", "10.100.25.1/24"), Bridge("vmbr1")],
    "storages": [],
}


def test_sections_cover_all_pages():
    """PAGE_SECTIONS associe chaque titre de page à sa section, titres uniques."""
    assert len(PAGE_SECTIONS) == len(PAGE_CLASSES) == 10
    assert PAGE_SECTIONS["Proxmox"] == "proxmox"
    assert PAGE_SECTIONS["Accès SSH aux nœuds"] == "nodes"
    assert PAGE_SECTIONS["Fédération LDAP externe"] == "ldap"


# --- Page Proxmox -----------------------------------------------------------


def proxmox_values(**over):
    """Valeurs valides de la page Proxmox."""
    base = {
        "proxmox.cluster_name": "labomatics",
        "proxmox.url": "https://pve1.lab:8006",
        "proxmox.user": "root@pam",
        "proxmox.token_id": "lab",
        "proxmox.token_secret": UUID,
    }
    return {**base, **over}


def test_proxmox_page_validation():
    """Nom, URL, utilisateur, token et secret sont validés."""
    w = make(
        ProxmoxPage(lambda *a: FakeApi(), lambda: {"pris"}),
        values=proxmox_values(
            **{
                "proxmox.cluster_name": "Pris",
                "proxmox.url": "http://x",
                "proxmox.user": "root",
                "proxmox.token_id": "1x",
                "proxmox.token_secret": "abc",
            }
        ),
    )
    assert submit(w)[0] is False
    for item in w.current.fields:
        assert item.error, item.key
    fill(w, {"proxmox.cluster_name": "pris"})
    name = field(w, "proxmox.cluster_name")
    name.validate()
    assert "existe déjà" in name.error


def test_proxmox_submit_fills_cache():
    """La soumission met nœuds, bridges et stockages en cache pour les pages suivantes."""
    api = FakeApi()
    w = make(ProxmoxPage(lambda *a: api), values=proxmox_values())
    assert submit(w) == (True, None)
    assert w.ctx.data["api"] is api
    assert [n.name for n in w.ctx.data["nodes"]] == ["pve1", "pve2"]
    assert w.ctx.data["bridges"][0].name == "vmbr0"
    assert w.ctx.data["storages"][0].name == "ceph"


def test_proxmox_submit_errors():
    """Nœud hors ligne et droits manquants donnent des erreurs distinctes."""
    offline = FakeApi(
        nodes=[ProxmoxNode("pve1", "online", ""), ProxmoxNode("pve2", "offline", "")]
    )
    ok, error = submit(make(ProxmoxPage(lambda *a: offline), values=proxmox_values()))
    assert "hors ligne" in error and "pve2" in error
    poor = FakeApi(missing=["Sys.Modify"])
    ok, error = submit(make(ProxmoxPage(lambda *a: poor), values=proxmox_values()))
    assert "Droits insuffisants" in error and "Sys.Modify" in error


# --- Pages VM / WAN / VXLAN --------------------------------------------------


def vm_values(**over):
    """Valeurs valides de la page VM."""
    base = {
        "vm.domain": "lab.example.fr",
        "vm.admin_iface": "vmbr0",
        "vm.admin_network": "10.100.25.0/24",
        "vm.admin_gateway": "10.100.25.254",
        "vm.vm_ip": "10.100.25.50",
    }
    return {**base, **over}


def test_vm_page_options_and_network_suggestion():
    """Les bridges ont un libellé avec CIDR ; le réseau est suggéré depuis l'interface."""
    w = make(
        VmPage(fake_checks(("10.100.25.254",))), NETWORK_DATA, {"vm.domain": "a.fr"}
    )
    iface = field(w, "vm.admin_iface")
    assert [label for _, label in iface.options] == [
        "vmbr0 (10.100.25.1/24)",
        "vmbr1 (sans IP)",
    ]
    assert field(w, "vm.admin_network").value == "10.100.25.0/24"
    iface.set_value("vmbr1")
    w.collect()
    assert field(w, "vm.admin_network").value == ""


def test_vm_page_validation_and_ping():
    """IP de la VM dans le réseau, ≠ passerelle, libre ; passerelle joignable."""
    checks = fake_checks(("10.100.25.254",))
    w = make(VmPage(checks), NETWORK_DATA, vm_values())
    assert submit(w) == (True, None)
    fill(w, {"vm.vm_ip": "10.100.25.254"})
    assert submit(w)[0] is False and "différent" in field(w, "vm.vm_ip").error
    fill(w, {"vm.vm_ip": "10.0.0.5"})
    assert submit(w)[0] is False and "hors du réseau" in field(w, "vm.vm_ip").error
    busy = make(
        VmPage(fake_checks(("10.100.25.254", "10.100.25.50"))),
        NETWORK_DATA,
        vm_values(),
    )
    assert "doit être libre" in submit(busy)[1]
    skipped = make(
        VmPage(fake_checks(("10.100.25.254", "10.100.25.50")), lambda: True),
        NETWORK_DATA,
        vm_values(),
    )
    assert submit(skipped) == (True, None)
    silent = make(VmPage(fake_checks()), NETWORK_DATA, vm_values())
    assert "passerelle" in submit(silent)[1]


def wan_values(**over):
    """Valeurs valides de la page WAN."""
    base = {
        "wan.iface": "vmbr1",
        "wan.network": "10.210.0.0/24",
        "wan.gateway": "10.210.0.1",
    }
    return {**base, **over}


def test_wan_page_checks():
    """Chevauchement, exclusions hors réseau et réseau saturé sont refusés."""
    assert submit(make(WanPage(), NETWORK_DATA, wan_values(), (VxlanPage(),))) == (
        True,
        None,
    )
    w = make(
        WanPage(),
        NETWORK_DATA,
        wan_values(**{"wan.network": "10.96.0.0/12", "wan.gateway": "10.96.0.1"}),
        (VxlanPage(),),
    )
    assert submit(w)[0] is False and "Chevauche" in field(w, "wan.network").error
    w = make(WanPage(), NETWORK_DATA, wan_values(), (VxlanPage(),))
    exclusions = field(w, "wan.exclusions")
    exclusions.input.text = "10.211.0.5"
    assert submit(w)[0] is False and "hors du réseau" in exclusions.error
    w = make(
        WanPage(),
        NETWORK_DATA,
        wan_values(
            **{
                "wan.network": "10.210.0.0/30",
                "wan.gateway": "10.210.0.1",
                "wan.exclusions": ["10.210.0.2"],
            }
        ),
        (VxlanPage(),),
    )
    ok, error = submit(w)
    assert ok and "Aucune IP allouable" in error


def test_address_pool_count():
    """Comptage des IP libres : passerelle et exclusions (plages fusionnées) retirées."""
    assert AddressPool("10.0.0.0/24", "10.0.0.1", []).free_count() == 253
    pool = AddressPool(
        "10.0.0.0/24", "10.0.0.1", ["10.0.0.2-10.0.0.10", "10.0.0.5-10.0.0.20"]
    )
    assert pool.free_count() == 253 - 19


def test_vxlan_page_checks_and_advanced_visibility():
    """Préfixe < 24, chevauchement, champs avancés conditionnels, zone existante."""
    api = FakeApi()
    data = {**NETWORK_DATA, "api": api, "storages": FakeApi().shared_storages()}
    w = make(
        VxlanPage(),
        data,
        {"vm.admin_network": "192.168.50.0/24"},
        (VmPage(fake_checks()), WanPage()),
    )
    assert not field(w, "vxlan.vni_min").visible
    assert field(w, "vxlan.storage").value == "ceph"
    assert submit(w) == (True, None), [(f.key, f.error) for f in w.steps[0].fields]
    fill(w, {"vxlan.advanced": True})
    assert field(w, "vxlan.vni_min").visible
    fill(w, {"vxlan.vni_min": "5000", "vxlan.vni_max": "4000"})
    assert submit(w)[0] is False and field(w, "vxlan.vni_max").error
    fill(w, {"vxlan.vni_max": "9000", "vxlan.network": "10.96.0.0/24"})
    assert submit(w)[0] is False and "/23" in field(w, "vxlan.network").error
    fill(w, {"vxlan.network": "192.168.0.0/16"})
    assert submit(w)[0] is False and "Chevauche" in field(w, "vxlan.network").error
    fill(w, {"vxlan.network": "10.96.0.0/12"})
    api.zones["labo"] = "vxlan"
    assert submit(w) == (True, None)
    api.zones["labo"] = "evpn"
    assert "evpn" in submit(w)[1]
    fill(w, {"vxlan.zone": "troplongue"})
    assert submit(w)[0] is False


# --- Admin / authentification / proxy ---------------------------------------


def test_admin_page_username_hint():
    """L'identifiant calculé s'affiche sous le nom."""
    w = make(
        AdminPage(), values={"admin.first_name": "Élodie", "admin.last_name": "Du Pont"}
    )
    assert (
        field(w, "admin.last_name")._hint_text()
        == "Identifiant de connexion : elodie.du-pont"
    )
    fill(w, {"admin.email": "pas-un-mail"})
    assert submit(w)[0] is False


def test_auth_radius_and_ldap_visibility():
    """RADIUS visible avec le LDAP local ; la page LDAP seulement avec le LDAP externe."""
    steps = [AuthPage().build(), LdapPage(fake_checks()).build()]
    w = Wizard("T", steps, recap=False)
    radius = field(w, "auth.radius")
    assert radius.visible and not w._visible.count(1)
    fill(w, {"auth.directory": "external"})
    assert not radius.visible and 1 in w._visible
    fill(w, {"auth.directory": "none"})
    assert not radius.visible and 1 not in w._visible


def test_ldap_page_submit_and_starttls():
    """Bind testé avec les valeurs saisies ; StartTLS caché en ldaps://."""
    checks = fake_checks()
    values = {
        "ldap.url": "ldap://ldap.lab:389",
        "ldap.base_dn": "dc=lab,dc=fr",
        "ldap.bind_dn": "cn=admin,dc=lab,dc=fr",
        "ldap.bind_password": "pw",
        "ldap.starttls": True,
    }
    w = make(LdapPage(checks), values=values)
    assert field(w, "ldap.starttls").visible
    assert submit(w) == (True, None)
    assert checks.ldap.calls == [
        ("ldap://ldap.lab:389", True, "cn=admin,dc=lab,dc=fr", "pw", "dc=lab,dc=fr")
    ]
    fill(w, {"ldap.url": "ldaps://ldap.lab"})
    assert not field(w, "ldap.starttls").visible
    checks.ldap.error = "bind LDAP refusé"
    assert submit(w) == (True, "bind LDAP refusé")


def test_ldap_is_saved_logic():
    """La page LDAP est « sauvegardée » quand elle est sans objet."""
    page = LdapPage(fake_checks())
    assert page.is_saved(InstallConfig.model_validate({"auth": {"directory": "local"}}))
    assert not page.is_saved(
        InstallConfig.model_validate({"auth": {"directory": "external"}})
    )


def test_proxy_page_validation():
    """Les hôtes de confiance sont des IP ou des CIDR."""
    w = make(ProxyPage(), values={"proxy.trusted_hosts": ["10.0.0.0/8"]})
    hosts = field(w, "proxy.trusted_hosts")
    hosts.input.text = "pas-une-ip"
    assert submit(w)[0] is False and hosts.error
    hosts.input.text = ""
    fill(w, {"proxy.trusted_hosts": ["10.0.0.0/8", "192.168.1.1"]})
    assert submit(w) == (True, None)


# --- E-mail ------------------------------------------------------------------


def test_mail_page_visibility_and_checks():
    """Champs visibles si activé ; SMTP puis Brevo testés."""
    checks = fake_checks()
    w = make(MailPage(checks))
    assert field(w, "mail.brevo_api_key").visible
    fill(w, {"mail.enabled": False})
    assert not field(w, "mail.smtp_host").visible
    assert submit(w) == (True, None) and not checks.smtp.calls
    fill(
        w,
        {
            "mail.enabled": True,
            "mail.brevo_api_key": "key",
            "mail.from_email": "no-reply@lab.fr",
            "mail.smtp_host": "smtp.lab.fr",
            "mail.smtp_user": "u",
            "mail.smtp_password": "p",
        },
    )
    assert submit(w) == (True, None)
    assert checks.smtp.calls == [("smtp.lab.fr", 587, True, "u", "p")]
    assert checks.brevo.calls == [("key",)]
    checks.brevo.error = "clé API Brevo invalide"
    assert submit(w) == (True, "clé API Brevo invalide")


# --- Nœuds -------------------------------------------------------------------


def test_nodes_page_factory_and_ssh_errors():
    """Trois champs par nœud ; chaque échec SSH est nommé."""
    checks = fake_checks()
    checks.ssh.fail_for = ("10.0.0.12",)
    data = {
        "nodes": [
            ProxmoxNode("pve1", "online", "10.0.0.11"),
            ProxmoxNode("pve2", "online", "10.0.0.12"),
        ]
    }
    w = make(NodesPage(checks), data)
    keys = [f.key for f in w.steps[0].fields]
    assert keys == [
        f"nodes.{n}.{k}" for n in ("pve1", "pve2") for k in ("user", "password", "host")
    ]
    assert field(w, "nodes.pve1.user").value == "root"
    assert field(w, "nodes.pve2.host").value == "10.0.0.12"
    assert submit(w)[0] is False
    fill(w, {"nodes.pve1.password": "a", "nodes.pve2.password": "b"})
    ok, error = submit(w)
    assert ok and error.startswith("pve2 : échec") and "pve1" not in error
    assert {c[0] for c in checks.ssh.calls} == {"10.0.0.11", "10.0.0.12"}
    assert NodesPage(checks).is_saved(InstallConfig()) is False

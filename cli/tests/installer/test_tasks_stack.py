import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from keycloak_fakes import FakeKeycloak
from labomatics_cli.installer.clusterconfig import ClusterConfigBuilder
from labomatics_cli.installer.stack import STACK_FILES, StackFiles
from labomatics_cli.installer.tasks.agent import AgentTask
from labomatics_cli.installer.tasks.backend import BackendTask
from labomatics_cli.installer.tasks.ca_propagation import CaPropagationTask
from labomatics_cli.installer.tasks.health import HealthTask
from labomatics_cli.installer.tasks.keycloak import PASSWORD_POLICY, KeycloakTask
from labomatics_cli.installer.tasks.proxmox_oidc import ProxmoxOidcTask
from labomatics_cli.installer.tasks.stack import StackTask
from labomatics_cli.models.install_config import InstallConfig
from task_fakes import CONFIG, FakeProxmox, make_ctx

DTO_PATH = (
    Path(__file__).resolve().parents[3] / "backend/labomatics/api/dto/cluster_config.py"
)


def variant(**sections):
    """Copie de la configuration de test avec des sections remplacées."""
    return {**CONFIG, **sections}


def test_stack_writes_files_generates_certs_and_starts(tmp_path):
    """Dépôt des fichiers (LDAP et RADIUS inclus), certificats, up puis attente."""
    sessions = []
    ctx = make_ctx(tmp_path, sessions=sessions)
    StackTask().run(ctx)
    ssh = sessions[0]
    assert "/etc/labomatics/docker-compose.yml" in ssh.files
    assert "/etc/labomatics/radius/clients.conf" in ssh.files
    assert "/etc/labomatics/ldap/bootstrap.ldif" in ssh.files
    assert "CN = *.lab.fr" in ssh.files["/tmp/labomatics-generate-certs.sh"]
    up = next(c for c in ssh.commands if "docker compose up -d" in c)
    assert "grep -vxE 'api|worker|frontend'" in up
    assert "keycloak.lab.fr" in ssh.files["/tmp/labomatics-wait-ready.sh"]
    assert any("clusters: []" in c for c in ssh.commands)


def test_stack_without_directory_skips_ldap_and_radius(tmp_path):
    """Sans annuaire : ni LDAP ni RADIUS dans les fichiers ni dans le compose."""
    sessions = []
    ctx = make_ctx(
        tmp_path, sessions=sessions, config=variant(auth={"directory": "none"})
    )
    StackTask().run(ctx)
    ssh = sessions[0]
    assert not any(
        "ldap" in p or "radius" in p for p in ssh.files if p.startswith("/etc")
    )
    assert "labomatics-ldap" not in ssh.files["/etc/labomatics/docker-compose.yml"]


def test_every_template_renders_with_strict_undefined(tmp_path):
    """Chaque template rend avec une configuration complète (variable manquante = erreur)."""
    for config in (CONFIG, variant(auth={"directory": "external"}, ldap=None)):
        ctx = make_ctx(tmp_path, config=config)
        files = StackFiles(ctx.config, ctx.store.secrets, ctx.templates)
        for item in STACK_FILES:
            files.render(item)
    ctx = make_ctx(tmp_path)
    ctx.templates.render("stack/init/generate-certs.sh.j2", domain="lab.fr")
    ctx.templates.render("stack/init/wait-ready.sh.j2", domain="lab.fr")


def test_templates_content(tmp_path):
    """TrustedIPs, SMTP/Brevo/timezone dans backend.env, secret Keycloak vide au départ."""
    ctx = make_ctx(tmp_path)
    files = StackFiles(ctx.config, ctx.store.secrets, ctx.templates)
    by_target = {f.target: files.render(f) for f in files.selected()}
    assert (
        "trustedIPs" in by_target["traefik.yml"]
        and "10.0.0.0/8" in by_target["traefik.yml"]
    )
    env = by_target["backend.env"]
    for expected in (
        "TIMEZONE=Europe/Paris",
        "BREVO_API_KEY=brevo-key",
        "BREVO_FROM_EMAIL=noreply@lab.fr",
        "SMTP_HOST=smtp.lab.fr",
        "SMTP_PORT=587",
        "SMTP_USER=smtpuser",
        "SMTP_PASSWORD=smtppw",
        "KEYCLOAK_CLIENT_SECRET=\n",
    ):
        assert expected in env
    assert "WAN_INTERFACE: vmbr1" in by_target["docker-compose.yml"]
    keycloak = yaml.safe_load(by_target["docker-compose.yml"])["services"]["keycloak"]
    assert keycloak["mem_limit"] == "4g"
    assert "-Xmx3g" in keycloak["environment"]["JAVA_OPTS_APPEND"]
    assert "dc=lab,dc=fr" in by_target["ldap/bootstrap.ldif"]


def test_ca_propagation_installs_then_is_idempotent(tmp_path):
    """CA copiée au premier passage ; empreinte identique : rien à faire."""
    sessions = []
    ctx = make_ctx(
        tmp_path, sessions=sessions, outputs={"cat /etc/labomatics": "CERT\n"}
    )
    CaPropagationTask().run(ctx)
    nodes = [s for s in sessions if s.args[1] == "root"]
    assert len(nodes) == 2
    assert all(
        s.files["/usr/local/share/ca-certificates/labomatics.crt"] == "CERT\n"
        and any("update-ca-certificates" in c for c in s.commands)
        for s in nodes
    )
    assert nodes[1].args[0] == "10.0.0.12"
    fingerprint = hashlib.sha256(b"CERT\n").hexdigest()
    sessions2 = []
    ctx2 = make_ctx(
        tmp_path / "b",
        sessions=sessions2,
        outputs={"cat /etc/labomatics": "CERT\n", "sha256sum": f"{fingerprint}  x\n"},
    )
    CaPropagationTask().run(ctx2)
    assert not any(s.files for s in sessions2)


def test_keycloak_creates_then_second_run_keeps_passwords(tmp_path):
    """Création complète puis seconde passe : mots de passe non réécrits, secret conservé."""
    kc = FakeKeycloak()
    ctx = make_ctx(tmp_path, keycloak=kc)
    KeycloakTask().run(ctx)
    secrets = ctx.store.secrets
    assert kc.realm_settings["passwordPolicy"] == PASSWORD_POLICY
    assert kc.realm_settings["smtpServer"]["host"] == "smtp.lab.fr"
    assert kc.passwords["u-jean.dupont"] == (secrets.admin_temp_password, True)
    assert "u-labomatics-admin" not in kc.passwords
    assert kc.clients["labomatics"]["serviceAccountsEnabled"] is True
    assert (
        "assign_client_roles",
        "sa-c-labomatics",
        "realm-management",
        ("manage-users", "view-users", "manage-clients", "view-clients"),
    ) in kc.calls
    assert kc.clients["labomatics"]["redirectUris"] == [
        "https://labomatics.lab.fr/*",
        "https://api.labomatics.lab.fr/v1/auth/callback",
    ]
    assert secrets.keycloak_client_secret == "secret-of-c-labomatics"
    provider = kc.components["ldap-labomatics"]["config"]
    assert provider["editMode"] == ["WRITABLE"] and provider["connectionUrl"] == [
        "ldap://ldap:389"
    ]
    assert provider["bindDn"] == ["cn=keycloak-bind,ou=svcaccounts,dc=lab,dc=fr"]
    assert provider["userObjectClasses"] == [
        "inetOrgPerson, organizationalPerson, person"
    ]
    assert {"username", "first name", "last name", "full name", "groups"} <= set(
        kc.components
    )
    assert kc.components["full name"]["config"]["write.only"] == ["true"]
    assert kc.components["groups"]["config"]["mode"] == ["LDAP_ONLY"]
    before = dict(kc.passwords)
    kc.passwords["u-jean.dupont"] = ("changed", False)
    KeycloakTask().run(ctx)
    assert kc.passwords["u-jean.dupont"] == ("changed", False)
    assert kc.passwords == {**before, "u-jean.dupont": ("changed", False)}


def test_keycloak_removes_legacy_service_user(tmp_path):
    """L'ancien utilisateur labomatics-admin d'une installation précédente est supprimé."""
    kc = FakeKeycloak()
    kc.users["labomatics-admin"] = "u-labomatics-admin"
    KeycloakTask().run(make_ctx(tmp_path, keycloak=kc))
    assert "labomatics-admin" not in kc.users


def test_keycloak_external_ldap_and_no_mail(tmp_path):
    """LDAP externe : paramètres saisis, StartTLS, sync ; sans mail : SMTP vidé."""
    ldap = {
        "url": "ldap://ad.lab.fr",
        "starttls": True,
        "base_dn": "dc=ext,dc=fr",
        "bind_dn": "cn=bind,dc=ext,dc=fr",
        "bind_password": "pw",
        "uuid_attr": "objectGUID",
        "periodic_sync": True,
    }
    kc = FakeKeycloak()
    ctx = make_ctx(
        tmp_path,
        keycloak=kc,
        config=variant(
            auth={"directory": "external"}, ldap=ldap, mail={"enabled": False}
        ),
    )
    KeycloakTask().run(ctx)
    config = kc.components["ldap-labomatics"]["config"]
    assert config["connectionUrl"] == ["ldap://ad.lab.fr"] and config["startTls"] == [
        "true"
    ]
    assert config["uuidLDAPAttribute"] == ["objectGUID"] and config[
        "changedSyncPeriod"
    ] == ["300"]
    assert config["usersDn"] == ["ou=users,dc=ext,dc=fr"]
    assert kc.realm_settings["smtpServer"] == {}


def test_keycloak_without_directory_has_no_federation(tmp_path):
    """Sans annuaire : aucun composant LDAP."""
    kc = FakeKeycloak()
    ctx = make_ctx(tmp_path, keycloak=kc, config=variant(auth={"directory": "none"}))
    KeycloakTask().run(ctx)
    assert kc.components == {}


def test_proxmox_oidc_creates_client_realm_and_admin(tmp_path):
    """Client proxmox-<cluster>, realm OIDC, utilisateur Administrator ; rejeu sans doublon."""
    kc, api = FakeKeycloak(), FakeProxmox()
    ctx = make_ctx(tmp_path, api, keycloak=kc)
    ctx.store.set_data("node_dns_entries", {"pve1.lab.fr": "10.0.0.11"})
    ProxmoxOidcTask().run(ctx)
    assert "https://pve1.lab.fr:8006/*" in kc.clients["proxmox-lab1"]["redirectUris"]
    assert (
        "configure_oidc_realm",
        "labomatics",
        "https://keycloak.lab.fr/realms/labomatics",
        "proxmox-lab1",
        "secret-of-c-proxmox-lab1",
    ) in api.calls
    assert ("grant", "/", "jean.dupont@labomatics", "Administrator") in api.calls
    api.calls.clear()
    ProxmoxOidcTask().run(ctx)
    assert "create_user" not in api.names()


def test_backend_writes_config_env_and_recreates(tmp_path):
    """Jeton backend, YAML 600, backend.env avec secret Keycloak, démarrage de l'app."""
    api, sessions = FakeProxmox(), []
    ctx = make_ctx(tmp_path, api, sessions)
    ctx.store.save_secret("keycloak_client_secret", "kc-secret")
    BackendTask().run(ctx)
    assert ("create_token", "labomatics@pve", "backend") in api.calls
    assert ctx.store.secrets.backend_token_secret == "secret-1"
    ssh = sessions[0]
    data = yaml.safe_load(ssh.files["/etc/labomatics/clusterconfig.yaml"])
    assert data["clusters"][0]["token_id"] == "labomatics@pve!backend"
    assert data["clusters"][0]["token_secret"] == "secret-1"
    assert (
        "KEYCLOAK_CLIENT_SECRET=kc-secret" in ssh.files["/etc/labomatics/backend.env"]
    )
    assert "--force-recreate api worker frontend" in ssh.commands[-1]
    api.calls.clear()
    BackendTask().run(ctx)
    assert "create_token" not in api.names() and "delete_token" not in api.names()


def test_clusterconfig_matches_backend_dto(tmp_path):
    """Le YAML généré est accepté par le DTO du backend."""
    if not DTO_PATH.exists():
        pytest.skip("backend absent")
    spec = importlib.util.spec_from_file_location("backend_dto", DTO_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["backend_dto"] = module
    spec.loader.exec_module(module)
    config = InstallConfig.model_validate(CONFIG)
    text = ClusterConfigBuilder(config).render("labomatics@pve!backend", "s")
    dto = module.ClusterConfigFileDTO(**yaml.safe_load(text))
    assert dto.clusters[0].default_storage == "ceph"
    assert dto.clusters[0].sdn_zone == "labo" and dto.wan[0].name == "lab1"
    assert dto.wan[0].exclusions == ["10.210.0.1-10.210.0.5"]
    assert dto.vnets[0].vni_max == 4000 and dto.clusters[0].vnet_config.name == "lab1"


def test_clusterconfig_reserves_admin_ips_in_shared_wan():
    """Réseau WAN = réseau admin : VM, passerelle admin et nœuds sont exclus."""
    wan = {
        **CONFIG["wan"],
        "network": "192.168.50.0/24",
        "gateway": "192.168.50.254",
        "exclusions": [],
    }
    nodes = {
        "pve1": {"password": "p", "host": "192.168.50.11"},
        "pve2": {"password": "p"},
    }
    config = InstallConfig.model_validate({**CONFIG, "wan": wan, "nodes": nodes})
    data = ClusterConfigBuilder(config).data("t", "s")
    assert data["wan"][0]["exclusions"] == ["192.168.50.10", "192.168.50.11"]


def test_agent_is_skipped(tmp_path):
    """L'agent n'est jamais nécessaire."""
    ctx = make_ctx(tmp_path)
    task = AgentTask()
    assert not task.is_needed(ctx) and "pas encore développé" in task.skip_reason


class FakeResponse:
    """Réponse HTTP factice."""

    def __init__(self, status=200, data=None):
        """Initialise la réponse."""
        self.status_code, self._data = status, data or {}

    def json(self):
        """Corps JSON."""
        return self._data


class FakeSession:
    """Session HTTP factice qui répond selon le chemin."""

    def __init__(self, issuer="https://keycloak.lab.fr/realms/labomatics", api=200):
        """Initialise la session."""
        self.issuer, self.api, self.verify, self.requests = issuer, api, True, []

    def get(self, url, headers=None, timeout=None):
        """Répond à /health ou à la découverte OIDC."""
        self.requests.append((url, headers["Host"]))
        if url.endswith("/health"):
            return FakeResponse(self.api)
        return FakeResponse(200, {"issuer": self.issuer})


def test_health_ok_exposes_final_summary(tmp_path):
    """Contrôles réussis : URLs, identifiant et mot de passe temporaire enregistrés."""
    api = FakeProxmox()
    api.realms["labomatics"] = "x"
    ctx = make_ctx(tmp_path, api)
    session = FakeSession()
    task = HealthTask(session, lambda name: ["192.168.50.10"], delay=0)
    assert task.recorded is False
    task.run(ctx)
    assert ("https://192.168.50.10/health", "api.labomatics.lab.fr") in session.requests
    summary = ctx.store.get_data("final_summary")
    assert summary["admin_username"] == "jean.dupont"
    assert summary["admin_temp_password"] == ctx.store.secrets.admin_temp_password
    assert summary["frontend_url"] == "https://labomatics.lab.fr"


def test_health_reports_every_failure(tmp_path):
    """Plusieurs contrôles en échec : tous sont listés dans l'erreur."""
    ctx = make_ctx(tmp_path, FakeProxmox())
    task = HealthTask(FakeSession(issuer="autre", api=500), lambda name: [], delay=0)
    with pytest.raises(RuntimeError) as err:
        task.run(ctx)
    text = str(err.value)
    assert "API /health" in text and "Découverte OIDC" in text
    assert "Realm OIDC Proxmox" in text and "DNS" not in text


def test_health_unresolved_names_only_warn(tmp_path):
    """Noms non résolus depuis le poste : avertissement avec la ligne hosts, pas d'échec."""
    api = FakeProxmox()
    api.realms["labomatics"] = "x"
    ctx = make_ctx(tmp_path, api)
    HealthTask(FakeSession(), lambda name: [], delay=0).run(ctx)
    warnings = [line.text for line in ctx.ui.lines if line.level == "warn"]
    assert any("fichier hosts" in m for m in warnings)
    assert (
        "192.168.50.10 keycloak.lab.fr labomatics.lab.fr api.labomatics.lab.fr"
        in warnings
    )
    assert ctx.store.get_data("final_summary") is not None

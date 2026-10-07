import paramiko
import pytest

from labomatics_cli.installer import ssh as ssh_module
from labomatics_cli.installer.ssh import CliKey, SshError, SshSession


def test_cli_key_is_generated_once_with_safe_permissions(tmp_path):
    """La clé ed25519 est créée en 600, réutilisée ensuite, et lisible par paramiko."""
    key = CliKey(tmp_path / "ssh" / "labomatics-cli")
    path = key.ensure()
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    public = key.public_key()
    assert public.startswith("ssh-ed25519 ") and public.endswith("labomatics-cli")
    assert CliKey(path).public_key() == public
    paramiko.Ed25519Key.from_private_key_file(str(path))


class FakeStream:
    """Flux de sortie factice avec code de retour."""

    def __init__(self, text, code=0):
        """Initialise le flux.

        Args:
            text: Contenu lu.
            code: Code de retour.
        """
        self._text = text
        self.channel = self
        self._code = code

    def read(self):
        """Lit le contenu.

        Returns:
            Le texte encodé.
        """
        return self._text.encode()

    def recv_exit_status(self):
        """Code de retour.

        Returns:
            Le code configuré.
        """
        return self._code


class FakeClient:
    """Faux client paramiko : échoue `failures` fois avant de se connecter."""

    failures = 0
    instances = []

    def __init__(self):
        """Mémorise l'instance."""
        self.connects = 0
        self.sftp = None
        FakeClient.instances.append(self)

    def set_missing_host_key_policy(self, policy):
        """Ignore la politique.

        Args:
            policy: Politique de clé d'hôte.
        """

    def connect(self, *args, **kwargs):
        """Échoue tant que des échecs restent programmés.

        Args:
            *args: Hôte.
            **kwargs: Options.

        Raises:
            OSError: Tant que `failures` est positif.
        """
        if FakeClient.failures > 0:
            FakeClient.failures -= 1
            raise OSError("refusé")

    def exec_command(self, command, timeout=None):
        """Simule une commande.

        Args:
            command: Commande.
            timeout: Délai.

        Returns:
            Entrée, sortie et erreur factices.
        """
        return None, FakeStream("ok", 1 if "bad" in command else 0), FakeStream("err")

    def close(self):
        """Simule la fermeture."""


@pytest.fixture
def fake_paramiko(monkeypatch):
    """Remplace le client paramiko par un faux."""
    FakeClient.failures, FakeClient.instances = 0, []
    monkeypatch.setattr(ssh_module.paramiko, "SSHClient", FakeClient)


def test_connect_retries_then_runs(fake_paramiko):
    """La connexion est retentée, `run` renvoie le résultat et lève si `check`."""
    FakeClient.failures = 2
    with SshSession("h", "u", retries=3, delay=0) as session:
        assert session.run("echo").stdout == "ok"
        assert not session.run("bad", check=False).ok
        with pytest.raises(SshError, match="err"):
            session.run("bad")


def test_connect_gives_up(fake_paramiko):
    """Après toutes les tentatives, une erreur française est levée."""
    FakeClient.failures = 5
    with pytest.raises(SshError, match="Connexion SSH impossible"):
        SshSession("h", "u", retries=2, delay=0).connect()


def test_run_requires_connection():
    """Sans connexion, `run` lève une erreur claire."""
    with pytest.raises(SshError, match="non connectée"):
        SshSession("h", "u").run("x")

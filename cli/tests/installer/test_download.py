import pytest

from labomatics_cli.installer.download import RemoteDownload
from labomatics_cli.installer.ssh import CommandResult


class ScriptedSsh:
    """Fausse session : réponses successives par préfixe de commande."""

    def __init__(self, replies):
        """Mémorise les réponses (préfixe -> liste de sorties consommées dans l'ordre)."""
        self.replies = {k: list(v) for k, v in replies.items()}
        self.commands = []

    def run(self, command, check=True, timeout=900):
        """Renvoie la prochaine sortie prévue pour ce préfixe, sinon une sortie vide."""
        self.commands.append(command)
        for prefix, outputs in self.replies.items():
            if command.startswith(prefix) and outputs:
                return CommandResult(outputs.pop(0), "", 0)
        return CommandResult("", "", 0)


def download(ssh, **kw):
    """Téléchargement sans attente réelle."""
    return RemoteDownload(
        ssh, "https://x/img.qcow2", "/c/img.qcow2", poll=30, sleep=lambda s: None, **kw
    )


def test_logs_percentage_until_done():
    """Un message de progression par intervalle, puis renommage du fichier."""
    ssh = ScriptedSsh(
        {
            "curl": ["480000000\n"],
            "cat": ["", "", "0\n"],
            "stat": ["100000000\n", "216000000\n"],
        }
    )
    logs = []
    download(ssh).run(logs.append)
    assert logs == [
        "Téléchargement lancé (480 Mo), progression toutes les 30 s",
        "Téléchargement : 20 % (100/480 Mo)",
        "Téléchargement : 45 % (216/480 Mo)",
    ]
    assert any("nohup sh -c 'wget" in c for c in ssh.commands)
    assert ssh.commands[-1].startswith("mv /c/img.qcow2.part /c/img.qcow2")


def test_unknown_size_logs_megabytes():
    """Sans taille annoncée, la progression est donnée en Mo reçus."""
    ssh = ScriptedSsh({"cat": ["", "0\n"], "stat": ["5000000\n"]})
    logs = []
    download(ssh).run(logs.append)
    assert logs[1:] == ["Téléchargement : 5 Mo reçus"]
    assert "taille inconnue" in logs[0]


def test_wget_failure_reports_log_tail():
    """Un code non nul remonte la fin du journal de wget."""
    ssh = ScriptedSsh(
        {"cat": ["4\n"], "tail": ["failed: Name or service not known.\n"]}
    )
    with pytest.raises(RuntimeError, match="code 4.*Name or service"):
        download(ssh).run(lambda m: None)


def test_unresolvable_server_fails_before_download():
    """DNS de l'hôte en panne : erreur explicite, wget n'est pas lancé."""

    class NoDns(ScriptedSsh):
        def run(self, command, check=True, timeout=900):
            self.commands.append(command)
            code = 2 if command.startswith("getent") else 0
            return CommandResult("", "", code)

    ssh = NoDns({})
    with pytest.raises(RuntimeError, match="ne résout pas x : vérifie son DNS"):
        download(ssh).run(lambda m: None)
    assert not any("wget" in c for c in ssh.commands)


def test_nothing_received_shows_wget_log():
    """Rien reçu : le message reprend la dernière ligne du journal de wget."""
    ssh = ScriptedSsh(
        {"cat": ["", "0\n"], "stat": [""], "tail": ["Connecting to x... \n"]}
    )
    logs = []
    download(ssh).run(logs.append)
    assert logs[1] == "Téléchargement : rien reçu pour l'instant Connecting to x..."


def test_first_check_is_quick():
    """Le premier contrôle a lieu après 5 s, les suivants à l'intervalle choisi."""
    waits = []
    ssh = ScriptedSsh({"cat": ["", "0\n"], "stat": ["1000000\n"]})
    RemoteDownload(ssh, "https://x/i", "/c/i", poll=30, sleep=waits.append).run(
        lambda m: None
    )
    assert waits == [5, 30]


def test_timeout_kills_wget():
    """Délai dépassé : wget est arrêté et une erreur est levée."""
    ssh = ScriptedSsh({})
    with pytest.raises(RuntimeError, match="trop long"):
        download(ssh, timeout=60).run(lambda m: None)
    assert any(c.startswith("pkill") for c in ssh.commands)

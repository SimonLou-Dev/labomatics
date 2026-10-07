"""Persistance de l'installation : configuration, état d'exécution et secrets d'un cluster."""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Collection, Mapping, Optional

import yaml
from pydantic import BaseModel

from labomatics_cli.installer.secrets import InstallSecrets, PasswordGenerator
from labomatics_cli.models.install_config import InstallConfig

DEFAULT_BASE_DIR = Path.home() / ".labomatics" / "clusters"


class InstallStatus(str, Enum):
    """Statut de la dernière exécution de l'installation."""

    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class InstallMode(str, Enum):
    """Mode de lancement du wizard : nouvelle install, reprise ou édition."""

    new = "new"
    resume = "resume"
    edit = "edit"


class InstallState(BaseModel):
    """Contenu de state.json : statut, tâches terminées, secrets et données d'exécution."""

    status: Optional[InstallStatus] = None
    installed_once: bool = False
    last_error: Optional[str] = None
    completed_tasks: list[str] = []
    secrets: InstallSecrets = InstallSecrets()
    data: dict[str, Any] = {}


class InstallStore:
    """Persistance d'un cluster : install.yaml (config) et state.json (état d'exécution)."""

    def __init__(self, directory: Path) -> None:
        """Ouvre (ou crée) le dossier du cluster et charge ses fichiers.

        Args:
            directory: Dossier du cluster, créé en chmod 700 s'il n'existe pas.
        """
        self.directory = directory
        self._config_path = directory / "install.yaml"
        self._state_path = directory / "state.json"
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        self._config = self._load_config()
        self._state = self._load_state()

    @classmethod
    def open(cls, cluster_name: str, base_dir: Optional[Path] = None) -> "InstallStore":
        """Ouvre le store d'un cluster par son nom.

        Args:
            cluster_name: Nom du cluster (nom du sous-dossier).
            base_dir: Dossier racine des clusters, `~/.labomatics/clusters` par défaut.

        Returns:
            Le store du cluster.
        """
        return cls((base_dir or DEFAULT_BASE_DIR) / cluster_name)

    @classmethod
    def list_clusters(cls, base_dir: Optional[Path] = None) -> list[str]:
        """Liste les clusters qui ont déjà une config ou un état sauvegardé.

        Args:
            base_dir: Dossier racine des clusters, `~/.labomatics/clusters` par défaut.

        Returns:
            Les noms de clusters, triés.
        """
        root = base_dir or DEFAULT_BASE_DIR
        if not root.is_dir():
            return []
        return sorted(
            p.name
            for p in root.iterdir()
            if (p / "install.yaml").exists() or (p / "state.json").exists()
        )

    def _load_config(self) -> InstallConfig:
        """Charge install.yaml.

        Returns:
            La configuration sauvegardée, ou une configuration vide.
        """
        if not self._config_path.exists():
            return InstallConfig()
        data = yaml.safe_load(self._config_path.read_text()) or {}
        return InstallConfig.model_validate(data)

    def _load_state(self) -> InstallState:
        """Charge state.json.

        Returns:
            L'état sauvegardé, ou un état vide.
        """
        if not self._state_path.exists():
            return InstallState()
        return InstallState.model_validate_json(self._state_path.read_text())

    def _write(self, path: Path, content: str) -> None:
        """Écrit un fichier de façon atomique, en chmod 600.

        Args:
            path: Fichier cible.
            content: Contenu texte à écrire.
        """
        tmp = path.with_name(path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    def _persist_state(self) -> None:
        """Sauvegarde l'état courant dans state.json."""
        self._write(
            self._state_path, json.dumps(self._state.model_dump(mode="json"), indent=2)
        )

    @property
    def config(self) -> InstallConfig:
        """Configuration courante du cluster.

        Returns:
            La configuration chargée ou dernièrement sauvegardée.
        """
        return self._config

    def save_config(self, config: InstallConfig) -> None:
        """Remplace et sauvegarde la configuration.

        Args:
            config: Nouvelle configuration complète.
        """
        self._config = config
        dumped = config.model_dump(mode="json", exclude_none=True)
        self._write(
            self._config_path,
            yaml.safe_dump(dumped, sort_keys=False, allow_unicode=True),
        )

    def save_page(
        self, values: Mapping[str, Any], section: Optional[str] = None
    ) -> InstallConfig:
        """Fusionne les valeurs d'une page du wizard dans la config et la sauvegarde.

        Args:
            values: Valeurs du wizard, clés plates « section.champ ».
            section: Si fourni, seules les clés de cette section sont appliquées.

        Returns:
            La configuration mise à jour.
        """
        self.save_config(self._config.merge_flat(values, section))
        return self._config

    @property
    def secrets(self) -> InstallSecrets:
        """Secrets du cluster, générés au premier accès puis conservés.

        Returns:
            Les secrets, jamais régénérés une fois créés.
        """
        ensured = self._state.secrets.ensure(PasswordGenerator())
        if ensured != self._state.secrets:
            self._state.secrets = ensured
            self._persist_state()
        return self._state.secrets

    def save_secret(self, name: str, value: str) -> None:
        """Enregistre un secret obtenu pendant l'installation (token, secret client…).

        Args:
            name: Nom du champ dans InstallSecrets.
            value: Valeur du secret.

        Raises:
            KeyError: Si le nom ne correspond à aucun secret connu.
        """
        if name not in InstallSecrets.model_fields:
            raise KeyError(name)
        self._state.secrets = self._state.secrets.model_copy(update={name: value})
        self._persist_state()

    @property
    def status(self) -> Optional[InstallStatus]:
        """Statut de la dernière exécution.

        Returns:
            Le statut, ou None si l'installation n'a jamais été lancée.
        """
        return self._state.status

    @property
    def last_error(self) -> Optional[str]:
        """Dernière erreur d'installation.

        Returns:
            Le message d'erreur, ou None.
        """
        return self._state.last_error

    def mark_in_progress(self) -> None:
        """Marque l'installation comme en cours et efface la dernière erreur."""
        self._state.status = InstallStatus.in_progress
        self._state.last_error = None
        self._persist_state()

    def mark_completed(self) -> None:
        """Marque l'installation comme terminée (le cluster passe en mode édition)."""
        self._state.status = InstallStatus.completed
        self._state.installed_once = True
        self._state.last_error = None
        self._persist_state()

    def mark_failed(self, error: str) -> None:
        """Marque l'installation comme échouée.

        Args:
            error: Message d'erreur à conserver.
        """
        self._state.status = InstallStatus.failed
        self._state.last_error = error
        self._persist_state()

    @property
    def is_installed(self) -> bool:
        """Indique si l'installation a déjà abouti au moins une fois.

        Returns:
            True si le cluster a été installé au moins une fois.
        """
        return self._state.installed_once

    @property
    def mode(self) -> InstallMode:
        """Mode de lancement du wizard déduit de l'état.

        Returns:
            `edit` si installé, `new` si rien n'est sauvegardé, sinon `resume`.
        """
        if self._state.status == InstallStatus.completed:
            return InstallMode.edit
        if self._state.status is None and not self._config.to_flat():
            return InstallMode.new
        return InstallMode.resume

    @property
    def completed_tasks(self) -> list[str]:
        """Tâches d'installation terminées, dans l'ordre.

        Returns:
            Une copie de la liste des noms de tâches.
        """
        return list(self._state.completed_tasks)

    def is_task_done(self, name: str) -> bool:
        """Indique si une tâche d'installation est déjà terminée.

        Args:
            name: Nom de la tâche.

        Returns:
            True si la tâche est terminée.
        """
        return name in self._state.completed_tasks

    def mark_task_done(self, name: str) -> None:
        """Marque une tâche comme terminée et sauvegarde.

        Args:
            name: Nom de la tâche.
        """
        if name not in self._state.completed_tasks:
            self._state.completed_tasks.append(name)
            self._persist_state()

    def forget_tasks(self, names: Collection[str]) -> None:
        """Oublie certaines tâches terminées (pour les rejouer) et sauvegarde.

        Args:
            names: Noms des tâches à oublier.
        """
        kept = [n for n in self._state.completed_tasks if n not in names]
        if kept != self._state.completed_tasks:
            self._state.completed_tasks = kept
            self._persist_state()

    def reset_tasks(self) -> None:
        """Oublie les tâches terminées (pour tout rejouer)."""
        self._state.completed_tasks = []
        self._persist_state()

    def get_data(self, key: str, default: Any = None) -> Any:
        """Lit une donnée d'exécution (VMID, identifiants créés…).

        Args:
            key: Nom de la donnée.
            default: Valeur renvoyée si la donnée est absente.

        Returns:
            La valeur sauvegardée ou `default`.
        """
        return self._state.data.get(key, default)

    def set_data(self, key: str, value: Any) -> None:
        """Enregistre une donnée d'exécution et sauvegarde.

        Args:
            key: Nom de la donnée.
            value: Valeur sérialisable en JSON.
        """
        self._state.data[key] = value
        self._persist_state()

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml
from pydantic import BaseModel

from labomatics_cli.installer.config import InstallConfig
from labomatics_cli.installer.secrets import InstallSecrets, PasswordGenerator

DEFAULT_BASE_DIR = Path.home() / ".labomatics" / "clusters"


class InstallStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class InstallMode(str, Enum):
    new = "new"
    resume = "resume"
    edit = "edit"


class InstallState(BaseModel):
    status: Optional[InstallStatus] = None
    installed_once: bool = False
    last_error: Optional[str] = None
    completed_tasks: list[str] = []
    secrets: InstallSecrets = InstallSecrets()
    data: dict[str, Any] = {}


class InstallStore:
    """Persistance d'un cluster : install.yaml (config) et state.json (état d'exécution)."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._config_path = directory / "install.yaml"
        self._state_path = directory / "state.json"
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        self._config = self._load_config()
        self._state = self._load_state()

    @classmethod
    def open(cls, cluster_name: str, base_dir: Optional[Path] = None) -> "InstallStore":
        return cls((base_dir or DEFAULT_BASE_DIR) / cluster_name)

    @classmethod
    def list_clusters(cls, base_dir: Optional[Path] = None) -> list[str]:
        root = base_dir or DEFAULT_BASE_DIR
        if not root.is_dir():
            return []
        return sorted(
            p.name
            for p in root.iterdir()
            if (p / "install.yaml").exists() or (p / "state.json").exists()
        )

    def _load_config(self) -> InstallConfig:
        if not self._config_path.exists():
            return InstallConfig()
        data = yaml.safe_load(self._config_path.read_text()) or {}
        return InstallConfig.model_validate(data)

    def _load_state(self) -> InstallState:
        if not self._state_path.exists():
            return InstallState()
        return InstallState.model_validate_json(self._state_path.read_text())

    def _write(self, path: Path, content: str) -> None:
        tmp = path.with_name(path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    def _persist_state(self) -> None:
        self._write(
            self._state_path, json.dumps(self._state.model_dump(mode="json"), indent=2)
        )

    @property
    def config(self) -> InstallConfig:
        return self._config

    def save_config(self, config: InstallConfig) -> None:
        self._config = config
        dumped = config.model_dump(mode="json", exclude_none=True)
        self._write(
            self._config_path,
            yaml.safe_dump(dumped, sort_keys=False, allow_unicode=True),
        )

    def save_page(
        self, values: Mapping[str, Any], section: Optional[str] = None
    ) -> InstallConfig:
        self.save_config(self._config.merge_flat(values, section))
        return self._config

    @property
    def secrets(self) -> InstallSecrets:
        ensured = self._state.secrets.ensure(PasswordGenerator())
        if ensured != self._state.secrets:
            self._state.secrets = ensured
            self._persist_state()
        return self._state.secrets

    def save_secret(self, name: str, value: str) -> None:
        if name not in InstallSecrets.model_fields:
            raise KeyError(name)
        self._state.secrets = self._state.secrets.model_copy(update={name: value})
        self._persist_state()

    @property
    def status(self) -> Optional[InstallStatus]:
        return self._state.status

    @property
    def last_error(self) -> Optional[str]:
        return self._state.last_error

    def mark_in_progress(self) -> None:
        self._state.status = InstallStatus.in_progress
        self._state.last_error = None
        self._persist_state()

    def mark_completed(self) -> None:
        self._state.status = InstallStatus.completed
        self._state.installed_once = True
        self._state.last_error = None
        self._persist_state()

    def mark_failed(self, error: str) -> None:
        self._state.status = InstallStatus.failed
        self._state.last_error = error
        self._persist_state()

    @property
    def is_installed(self) -> bool:
        return self._state.installed_once

    @property
    def mode(self) -> InstallMode:
        if self._state.status == InstallStatus.completed:
            return InstallMode.edit
        if self._state.status is None and not self._config.to_flat():
            return InstallMode.new
        return InstallMode.resume

    @property
    def completed_tasks(self) -> list[str]:
        return list(self._state.completed_tasks)

    def is_task_done(self, name: str) -> bool:
        return name in self._state.completed_tasks

    def mark_task_done(self, name: str) -> None:
        if name not in self._state.completed_tasks:
            self._state.completed_tasks.append(name)
            self._persist_state()

    def reset_tasks(self) -> None:
        self._state.completed_tasks = []
        self._persist_state()

    def get_data(self, key: str, default: Any = None) -> Any:
        return self._state.data.get(key, default)

    def set_data(self, key: str, value: Any) -> None:
        self._state.data[key] = value
        self._persist_state()

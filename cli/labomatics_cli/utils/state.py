"""Gestion de l'état de l'installation (persistence)."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class InstallState:
    """Sauvegarde et restaure l'état d'une installation."""

    def __init__(self, state_file: Path = None):
        """Initialiser le gestionnaire d'état."""
        if state_file is None:
            state_file = Path.home() / ".labomatics" / "install-state.json"
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Charger l'état depuis le fichier."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        """Sauvegarder l'état dans le fichier."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def set(self, key: str, value: Any) -> None:
        """Définir une valeur et sauvegarder."""
        self.data[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        """Récupérer une valeur."""
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """Vérifier si une clé existe."""
        return key in self.data

    def set_step(self, step_num: int, data: Dict[str, Any]) -> None:
        """Sauvegarder une étape complète."""
        if "steps" not in self.data:
            self.data["steps"] = {}
        self.data["steps"][str(step_num)] = data
        self.save()

    def get_step(self, step_num: int) -> Optional[Dict[str, Any]]:
        """Récupérer une étape sauvegardée."""
        steps = self.data.get("steps", {})
        return steps.get(str(step_num))

    def get_last_completed_step(self) -> int:
        """Retourner le dernier numéro d'étape complétée."""
        steps = self.data.get("steps", {})
        if not steps:
            return 0
        # Filtrer les clés numériques uniquement
        numeric_steps = [int(k) for k in steps.keys() if k.isdigit()]
        return max(numeric_steps) if numeric_steps else 0

    def is_in_progress(self) -> bool:
        """Vérifier si une installation est en cours."""
        return self.data.get("status") == "in_progress"

    def mark_in_progress(self, domain: str) -> None:
        """Marquer une installation comme en cours."""
        self.data["status"] = "in_progress"
        self.data["domain"] = domain
        self.data["started_at"] = datetime.now().isoformat()
        self.save()

    def mark_completed(self) -> None:
        """Marquer une installation comme complétée."""
        self.data["status"] = "completed"
        self.data["completed_at"] = datetime.now().isoformat()
        self.save()

    def mark_failed(self, error: str) -> None:
        """Marquer une installation comme échouée."""
        self.data["status"] = "failed"
        self.data["failed_at"] = datetime.now().isoformat()
        self.data["error"] = error
        self.save()

    def clear(self) -> None:
        """Effacer l'état (pour redémarrer)."""
        self.state_file.unlink(missing_ok=True)
        self.data = {}

"""Gestion de la configuration CLI."""

from pathlib import Path
from typing import Optional
import json


class ConfigManager:
    """Gère la configuration du CLI."""

    CONFIG_DIR = Path.home() / ".labomatics"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    @classmethod
    def ensure_config_dir(cls) -> None:
        """Créer le répertoire de config s'il n'existe pas."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def save_cluster_config(cls, name: str, url: str, user: str, token: str) -> None:
        """Sauvegarder la config d'un cluster."""
        cls.ensure_config_dir()
        config = cls.load_config()
        config["clusters"] = config.get("clusters", {})
        config["clusters"][name] = {
            "url": url,
            "user": user,
            # Token pas stocké (trop risqué) — utiliser env var
        }
        with open(cls.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    @classmethod
    def load_config(cls) -> dict:
        """Charger la config."""
        cls.ensure_config_dir()
        if cls.CONFIG_FILE.exists():
            with open(cls.CONFIG_FILE) as f:
                return json.load(f)
        return {}

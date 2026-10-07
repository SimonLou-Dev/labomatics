"""Définitions des templates VM, lues dans `templates/vm/*.yaml` à la racine du repo."""

from __future__ import annotations

import os
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from ..models import TempalteConfig

ENV_DIR = "LABOMATICS_TEMPLATES_DIR"
REPO_DIR = Path(__file__).resolve().parents[5] / "templates"


class VmTemplateCatalog:
    """Catalogue des templates VM décrits en YAML (un fichier par template)."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialise le catalogue.

        Args:
            root: Dossier `templates/` ; par défaut `$LABOMATICS_TEMPLATES_DIR`,
                sinon le dossier `templates/` à la racine du repo.
        """
        env = os.environ.get(ENV_DIR)
        self.root = root or (Path(env) if env else REPO_DIR)

    def load(self) -> list[TempalteConfig]:
        """Charge les templates VM, triés par nom de fichier.

        Returns:
            Une configuration par fichier `vm/*.yaml` ; liste vide si le dossier manque.
        """
        folder = self.root / "vm"
        return [
            TempalteConfig.model_validate(yaml.safe_load(path.read_text()))
            for path in sorted(folder.glob("*.yaml"))
        ]


images_list = VmTemplateCatalog().load()

__all__ = ["VmTemplateCatalog", "images_list"]

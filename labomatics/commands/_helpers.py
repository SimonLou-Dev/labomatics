#!/usr/bin/env python3
"""
Helpers partagés entre toutes les sous-commandes CLI.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from ..config import InfraConfig

console = Console()


def _find_students_csv(config: "InfraConfig") -> Path:
    """Résout le chemin du CSV étudiants (relatif à infra.yaml ou absolu)."""
    csv_str = config.openwrt.students_csv
    csv_path = Path(csv_str)
    if csv_path.is_absolute():
        return csv_path
    # Chercher à côté de infra.yaml
    for candidate in [
        Path("/etc/labomatics") / csv_str,
        Path.cwd() / csv_str,
        Path(__file__).parent.parent.parent / csv_str,
    ]:
        if candidate.exists():
            return candidate
    # Retourner le path dans le répertoire courant même s'il n'existe pas
    return Path.cwd() / csv_str


def make_connection():
    """Crée la connexion Proxmox depuis la configuration."""
    from ..config import load_proxmox_settings
    from ..proxmox import connect

    settings = load_proxmox_settings()
    return connect(settings)


def load_students_from_config(config: "InfraConfig"):
    """Charge les étudiants depuis le CSV référencé dans infra.yaml."""
    from ..students import load_students

    csv_path = _find_students_csv(config)
    return load_students(csv_path)


def ask_confirm(message: str) -> bool:
    """Demande une confirmation interactive à l'utilisateur."""
    try:
        answer = input(f"\n{message} [y/N] ").strip().lower()
        return answer in ("y", "yes", "o", "oui")
    except (EOFError, KeyboardInterrupt):
        return False

#!/usr/bin/env python3
"""
Utilitaires partagés entre toutes les commandes CLI.

Ce module fournit les fonctions d'initialisation communes (connexion Proxmox,
chargement du CSV, confirmation interactive) utilisées par chaque commande.
"""

from pathlib import Path

from rich.console import Console

from ..config import load_config, load_proxmox_settings
from ..proxmox import connect
from ..students import Student, load_students

console = Console()


def make_connection():
    """Charge la configuration et ouvre une connexion Proxmox.

    Returns:
        Tuple ``(proxmox, infra_config)`` prêt à l'emploi.
    """
    settings = load_proxmox_settings()
    config = load_config()
    proxmox = connect(settings)
    return proxmox, config


def load_students_from_config(config) -> list[Student]:
    """Charge les étudiants depuis le CSV défini dans la configuration.

    Affiche le nombre d'étudiants chargés sur la console.

    Args:
        config: Configuration de l'infrastructure.

    Returns:
        Liste d'objets :class:`~esgilabs.students.Student` triés par ``id``.
    """
    csv_path = Path(__file__).parent.parent.parent / config.openwrt.students_csv
    students = load_students(csv_path)
    console.print(f"  [dim]{len(students)} étudiant(s) — {csv_path.name}[/dim]\n")
    return students


def ask_confirm() -> bool:
    """Demande confirmation interactive à l'opérateur.

    Returns:
        ``True`` si l'opérateur confirme (y/yes/o/oui), ``False`` sinon.
    """
    try:
        ans = console.input("[bold]Appliquer ? [y/N][/bold] ").strip().lower()
        return ans in ("y", "yes", "o", "oui")
    except (EOFError, KeyboardInterrupt):
        return False

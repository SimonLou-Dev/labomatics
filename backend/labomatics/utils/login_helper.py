"""Utilitaires pour la génération de login, passwords et années scolaires."""

import secrets
import string
from datetime import datetime


def generate_login(first_name: str, last_name: str) -> str:
    """Génère un login au format firstname.lastname."""
    first = first_name.strip().lower()
    last = last_name.strip().lower()
    return f"{first}.{last}"


def generate_password(length: int = 12) -> str:
    """Génère un password aléatoire sécurisé."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_school_year() -> tuple[int, int]:
    """Retourne (year, start_date, end_date) de l'année scolaire courante.

    Année scolaire: 01/09/year à 31/08/year+1
    Si avant 01/09: année scolaire précédente
    Si après 01/09: année scolaire courante
    """
    now = datetime.now()

    # Si avant 01/09, on est dans l'année scolaire précédente
    if now.month < 9:
        year = now.year - 1
    else:
        year = now.year

    start_date = datetime(year, 9, 1)
    end_date = datetime(year + 1, 8, 31)

    return year, start_date, end_date

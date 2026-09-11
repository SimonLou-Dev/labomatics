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
    """Génère un password aléatoire sécurisé avec au moins une majuscule, minuscule et chiffre."""
    if length < 3:
        length = 12

    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*"

    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
    ]
    alphabet = uppercase + lowercase + digits + special
    password += [secrets.choice(alphabet) for _ in range(length - 3)]

    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def get_school_year() -> tuple[int, datetime, datetime]:
    """Retourne (year, start_date, end_date) de l'année scolaire courante.

    Année scolaire: 01/09/year à 31/08/year+1
    Si avant 01/09: année scolaire précédente
    Si après 01/09: année scolaire courante
    """
    now = datetime.now()

    year = now.year - 1 if now.month < 9 else now.year

    start_date = datetime(year, 9, 1)
    end_date = datetime(year + 1, 8, 31)

    return year, start_date, end_date

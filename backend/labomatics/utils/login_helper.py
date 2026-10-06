"""Utilitaires pour la génération de login, passwords et années scolaires."""

import re
import secrets
import string
import unicodedata
from datetime import datetime

UPPERCASE = string.ascii_uppercase
LOWERCASE = string.ascii_lowercase
DIGITS = string.digits
SPECIAL = "!@#$%^&*"

REQUIRED_CLASSES = (UPPERCASE, LOWERCASE, DIGITS, SPECIAL)


def generate_login(first_name: str, last_name: str) -> str:
    """Génère un login au format firstname.lastname (sanitisé sans accents)."""
    first = first_name.strip().lower()
    last = last_name.strip().lower()
    login = f"{first}.{last}"

    # Enlever les accents, trémas et autres caractères spéciaux
    login = (
        unicodedata.normalize("NFKD", login).encode("ascii", "ignore").decode("ascii")
    )
    # Enlever les apostrophes et autres caractères non-alphanumériques
    login = re.sub(r"[^a-z0-9._-]", "", login)
    return login


def generate_password(length: int = 12) -> str:
    """Génère un mot de passe aléatoire contenant au moins un caractère
    de chaque classe : majuscule, minuscule, chiffre et caractère spécial."""
    if length < len(REQUIRED_CLASSES):
        # Échouer explicitement plutôt que de changer la longueur en silence
        raise ValueError(
            f"length doit valoir au moins {len(REQUIRED_CLASSES)}, reçu {length}"
        )

    # Un caractère garanti par classe exigée par la politique
    password = [secrets.choice(charset) for charset in REQUIRED_CLASSES]

    # Complète avec des caractères tirés de toutes les classes
    alphabet = "".join(REQUIRED_CLASSES)
    password += [secrets.choice(alphabet) for _ in range(length - len(password))]

    # Mélange pour que les caractères garantis ne soient pas toujours en tête
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

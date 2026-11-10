"""Utilitaires pour la génération de login, passwords et années scolaires."""

import re
import secrets
import string
import unicodedata
from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class PasswordPolicy:
    """Contraintes de mot de passe (sous-ensemble de la `passwordPolicy` Keycloak)."""

    length: int = 16
    max_length: int | None = None
    min_upper: int = 2
    min_lower: int = 3
    min_digits: int = 2
    min_special: int = 2

    @property
    def min_required(self) -> int:
        """Nombre de caractères imposés par les minimums de classes."""
        return self.min_upper + self.min_lower + self.min_digits + self.min_special


DEFAULT_PASSWORD_POLICY = PasswordPolicy()
DEFAULT_PASSWORD_LENGTH = 20

# Politique Keycloak : "length(16) and specialChars(2) and upperCase(2) ..."
_POLICY_TERM = re.compile(r"(\w+)\((\d+)\)")
_POLICY_FIELDS = {
    "length": "length",
    "maxLength": "max_length",
    "upperCase": "min_upper",
    "lowerCase": "min_lower",
    "digits": "min_digits",
    "specialChars": "min_special",
}


def parse_password_policy(policy: str | None) -> PasswordPolicy:
    """Convertit une `passwordPolicy` Keycloak en `PasswordPolicy`.

    Les règles non gérées (`passwordHistory`, `notUsername`, ...) sont ignorées :
    un mot de passe aléatoire les respecte de fait. Les règles absentes gardent
    les valeurs par défaut, si bien qu'un realm sans politique (ou illisible)
    produit quand même un mot de passe robuste.
    """
    if not policy:
        return DEFAULT_PASSWORD_POLICY

    values: dict[str, int] = {}
    for name, raw in _POLICY_TERM.findall(policy):
        field = _POLICY_FIELDS.get(name)
        if field:
            values[field] = int(raw)
    return replace(DEFAULT_PASSWORD_POLICY, **values)


def generate_password(
    policy: PasswordPolicy | None = None, length: int | None = None
) -> str:
    """Génère un mot de passe aléatoire conforme à `policy`.

    Chaque classe (majuscule, minuscule, chiffre, spécial) reçoit au moins son
    minimum ; le reste est tiré dans toutes les classes puis l'ensemble est
    mélangé. Sans `length`, la longueur vaut `DEFAULT_PASSWORD_LENGTH`, relevée
    au besoin pour satisfaire la politique et plafonnée par `max_length`.
    """
    policy = policy or DEFAULT_PASSWORD_POLICY

    if length is None:
        length = max(DEFAULT_PASSWORD_LENGTH, policy.length, policy.min_required)
        if policy.max_length is not None:
            length = min(length, policy.max_length)

    # Échouer explicitement plutôt que de produire un mot de passe refusé
    lower_bound = max(policy.length, policy.min_required)
    if length < lower_bound:
        raise ValueError(f"length doit valoir au moins {lower_bound}, reçu {length}")
    if policy.max_length is not None and length > policy.max_length:
        raise ValueError(
            f"length doit valoir au plus {policy.max_length}, reçu {length}"
        )

    minimums = (
        (UPPERCASE, policy.min_upper),
        (LOWERCASE, policy.min_lower),
        (DIGITS, policy.min_digits),
        (SPECIAL, policy.min_special),
    )
    password = [secrets.choice(chars) for chars, n in minimums for _ in range(n)]

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

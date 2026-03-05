#!/usr/bin/env python3
"""
Gestion du fichier CSV des credentials étudiants.

Format du CSV : ``nom,userid,password,wan_ip``

Règle d'idempotence : si un étudiant est déjà dans ``credentials.csv``,
son mot de passe existant est conservé lors d'un apply.

.. warning::
    Le fichier ``credentials.csv`` contient des mots de passe en clair.
    Ne pas le versionner (ajouter à ``.gitignore``).
"""

import csv
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import InfraConfig
    from .students import Student


def _find_students_csv(config: "InfraConfig") -> Path:
    """Résout le chemin du CSV étudiants."""
    csv_str = config.openwrt.students_csv
    csv_path = Path(csv_str)
    if csv_path.is_absolute():
        return csv_path
    for candidate in [
        Path("/etc/labomatics") / csv_str,
        Path.cwd() / csv_str,
        Path(__file__).parent.parent / csv_str,
    ]:
        if candidate.exists():
            return candidate
    return Path.cwd() / csv_str


def creds_path(config: "InfraConfig") -> Path:
    """Retourne le chemin absolu vers ``credentials.csv`` (à côté de students.csv)."""
    students_csv = _find_students_csv(config)
    return students_csv.parent / "credentials.csv"


def load_credentials(config: "InfraConfig") -> dict[str, dict]:
    """Charge les credentials existants depuis ``credentials.csv``.

    Returns:
        Dictionnaire ``{nom: {nom, userid, password, wan_ip}}``.
        Dictionnaire vide si le fichier n'existe pas.
    """
    path = creds_path(config)
    if not path.exists():
        return {}
    creds: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Rétrocompatibilité : ancien format utilisait "nom" comme clé login
            d = dict(row)
            if "login" not in d:
                d["login"] = d.get("nom", "")
            key = d["login"]
            if key:
                creds[key] = d
    return creds


def save_credentials(config: "InfraConfig", creds: dict[str, dict]) -> Path:
    """Écrit le CSV credentials (nom, userid, password, wan_ip).

    Les lignes sont triées par nom alphabétiquement.

    Returns:
        Chemin du fichier écrit.
    """
    path = creds_path(config)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["login", "nom", "userid", "password", "wan_ip"])
        writer.writeheader()
        for row in sorted(creds.values(), key=lambda r: r["login"]):
            writer.writerow(row)
    return path


def generate_password() -> str:
    """Génère un mot de passe aléatoire sécurisé (16 caractères URL-safe)."""
    return secrets.token_urlsafe(12)


def make_credential(student: "Student", password: str, wan_ip: str) -> dict:
    """Construit un enregistrement de credential pour un étudiant."""
    return {
        "login": student.login(),
        "nom": f"{student.prenom} {student.nom}".strip(),
        "userid": student.user_id(),
        "password": password,
        "wan_ip": wan_ip,
    }

#!/usr/bin/env python3
"""
Gestion du fichier CSV des credentials étudiants.

Lors de l'exécution de ``apply``, un compte Proxmox est créé pour chaque
nouvel étudiant avec un mot de passe généré aléatoirement. Ces credentials
sont persistés dans ``credentials.csv`` (à côté de ``students.csv``) pour
pouvoir être distribués aux étudiants.

Format du CSV : ``nom,userid,password,wan_ip``

Règle d'idempotence : si un étudiant est déjà dans ``credentials.csv``,
son mot de passe existant est conservé (le compte Proxmox n'est pas recréé).

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


def creds_path(config: "InfraConfig") -> Path:
    """Retourne le chemin absolu vers ``credentials.csv``.

    Le fichier est placé dans le même répertoire que ``students.csv``.

    Args:
        config: Configuration de l'infrastructure.

    Returns:
        Chemin vers ``credentials.csv``.
    """
    students_csv = Path(__file__).parent.parent / config.openwrt.students_csv
    return students_csv.parent / "credentials.csv"


def load_credentials(config: "InfraConfig") -> dict[str, dict]:
    """Charge les credentials existants depuis ``credentials.csv``.

    Args:
        config: Configuration de l'infrastructure.

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
            creds[row["nom"]] = dict(row)
    return creds


def save_credentials(config: "InfraConfig", creds: dict[str, dict]) -> Path:
    """Écrit le CSV credentials (nom, userid, password, wan_ip).

    Les lignes sont triées par nom alphabétiquement.

    Args:
        config: Configuration de l'infrastructure.
        creds: Dictionnaire ``{nom: {nom, userid, password, wan_ip}}``.

    Returns:
        Chemin du fichier écrit.
    """
    path = creds_path(config)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nom", "userid", "password", "wan_ip"])
        writer.writeheader()
        for row in sorted(creds.values(), key=lambda r: r["nom"]):
            writer.writerow(row)
    return path


def generate_password() -> str:
    """Génère un mot de passe aléatoire sécurisé (16 caractères URL-safe).

    Utilise :func:`secrets.token_urlsafe` pour garantir une entropie suffisante.

    Returns:
        Chaîne de 16 caractères alphanumériques + ``-`` et ``_``.
    """
    return secrets.token_urlsafe(12)


def make_credential(student: "Student", password: str, wan_ip: str) -> dict:
    """Construit un enregistrement de credential pour un étudiant.

    Args:
        student: L'étudiant concerné.
        password: Mot de passe en clair généré pour cet étudiant.
        wan_ip: IP WAN allouée à l'étudiant.

    Returns:
        Dictionnaire ``{nom, userid, password, wan_ip}``.
    """
    return {
        "nom": student.nom,
        "userid": student.user_id(),
        "password": password,
        "wan_ip": wan_ip,
    }

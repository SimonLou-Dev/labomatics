"""Chiffrement/déchiffrement des secrets sensibles."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from labomatics.core.config.settings import settings


def _get_cipher() -> Fernet:
    """Retourne un cipher Fernet basé sur encryption_key."""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.encryption_key.encode()).digest()
    )
    return Fernet(key)


def encrypt_secret(plain: str) -> bytes:
    """Chiffre une chaîne et retourne les octets chiffrés."""
    return _get_cipher().encrypt(plain.encode())


def decrypt_secret(data: bytes) -> str:
    """Déchiffre des octets et retourne la chaîne originale."""
    return _get_cipher().decrypt(data).decode()

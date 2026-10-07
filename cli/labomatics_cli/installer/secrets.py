"""Génération et conservation des secrets d'installation."""

import secrets as _secrets
from typing import ClassVar, Optional

from pydantic import BaseModel


class PasswordGenerator:
    """Mots de passe conformes à la politique du realm Keycloak."""

    SPECIALS = "-_+.^~"
    UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    LOWER = "abcdefghijkmnopqrstuvwxyz"
    DIGITS = "23456789"

    def __init__(self, length: int = 24) -> None:
        """Initialise le générateur.

        Args:
            length: Longueur des mots de passe (16 minimum).

        Raises:
            ValueError: Si la longueur est inférieure à 16.
        """
        if length < 16:
            raise ValueError("length must be >= 16")
        self.length = length
        self._rng = _secrets.SystemRandom()

    def generate(self) -> str:
        """Génère un mot de passe conforme à la politique du realm.

        Returns:
            Un mot de passe mêlant majuscules, minuscules, chiffres et spéciaux.
        """
        pools = [(self.SPECIALS, 3), (self.UPPER, 3), (self.DIGITS, 3), (self.LOWER, 4)]
        chars = [_secrets.choice(pool) for pool, count in pools for _ in range(count)]
        everything = self.SPECIALS + self.UPPER + self.LOWER + self.DIGITS
        chars += [_secrets.choice(everything) for _ in range(self.length - len(chars))]
        self._rng.shuffle(chars)
        if chars[0] in self.SPECIALS:
            swap = next(i for i, c in enumerate(chars) if c not in self.SPECIALS)
            chars[0], chars[swap] = chars[swap], chars[0]
        return "".join(chars)

    def token(self) -> str:
        """Génère un jeton aléatoire.

        Returns:
            Un jeton URL-safe de 32 octets.
        """
        return _secrets.token_urlsafe(32)


class InstallSecrets(BaseModel):
    """Secrets générés ou obtenus pendant l'installation."""

    vm_password: Optional[str] = None
    pg_root_password: Optional[str] = None
    labomatics_db_password: Optional[str] = None
    keycloak_db_password: Optional[str] = None
    keycloak_admin_password: Optional[str] = None
    ldap_admin_password: Optional[str] = None
    ldap_keycloak_bind_password: Optional[str] = None
    ldap_radius_bind_password: Optional[str] = None
    radius_shared_secret: Optional[str] = None
    admin_temp_password: Optional[str] = None
    encryption_key: Optional[str] = None
    labomatics_token_secret: Optional[str] = None
    backend_token_secret: Optional[str] = None
    keycloak_client_secret: Optional[str] = None

    PASSWORDS: ClassVar[tuple[str, ...]] = (
        "vm_password",
        "pg_root_password",
        "labomatics_db_password",
        "keycloak_db_password",
        "keycloak_admin_password",
        "ldap_admin_password",
        "ldap_keycloak_bind_password",
        "ldap_radius_bind_password",
        "radius_shared_secret",
        "admin_temp_password",
    )

    def ensure(self, generator: PasswordGenerator) -> "InstallSecrets":
        """Complète les secrets manquants sans toucher à ceux qui existent.

        Args:
            generator: Générateur de mots de passe et de jetons.

        Returns:
            Une copie avec tous les mots de passe et la clé de chiffrement renseignés.
        """
        updates: dict[str, str] = {}
        for name in self.PASSWORDS:
            if not getattr(self, name):
                updates[name] = generator.generate()
        if not self.encryption_key:
            updates["encryption_key"] = generator.token()
        return self.model_copy(update=updates)

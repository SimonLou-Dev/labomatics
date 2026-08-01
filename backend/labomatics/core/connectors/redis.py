"""Connecteur Redis pour les sessions et cache."""

from __future__ import annotations

import json
from typing import Any

import redis

from labomatics.core.config.settings import settings


class RedisConnector:
    """Connecteur Redis pour les sessions OAuth2, cache, etc."""

    def __init__(self, url: str | None = None):
        """Initialise la connexion Redis."""
        self.url = url or settings.redis_url
        self.client = redis.from_url(self.url, decode_responses=True)

    def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
    ) -> None:
        """Stocke une valeur avec expiration optionnelle (en secondes)."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.client.set(key, value, ex=ex)

    def get(self, key: str) -> str | None:
        """Récupère une valeur."""
        return self.client.get(key)

    def get_json(self, key: str) -> dict | list | None:
        """Récupère et désérialise une valeur JSON."""
        value = self.client.get(key)
        if value:
            return json.loads(value)
        return None

    def delete(self, key: str) -> int:
        """Supprime une clé. Retourne le nombre de clés supprimées."""
        return self.client.delete(key)

    def exists(self, key: str) -> bool:
        """Vérifie si une clé existe."""
        return self.client.exists(key) > 0

    def close(self) -> None:
        """Ferme la connexion."""
        self.client.close()

#!/usr/bin/env python3
"""
Connexion au cluster Proxmox et constante POOL_MARKER.
"""

from proxmoxer import ProxmoxAPI

from ..config import ProxmoxSettings

#: Marqueur injecté dans le champ ``comment`` de chaque pool créé par labomatics.
#: Permet de distinguer les pools gérés automatiquement des pools créés manuellement.
POOL_MARKER = "labomatics-managed"


def connect(settings: ProxmoxSettings) -> ProxmoxAPI:
    """Crée et retourne un client ProxmoxAPI authentifié par token."""
    user, token_name = settings.token_id.split("!")
    return ProxmoxAPI(
        settings.host,
        user=user,
        token_name=token_name,
        token_value=settings.token_secret,
        verify_ssl=False,
    )

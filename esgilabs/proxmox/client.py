#!/usr/bin/env python3
"""
Connexion au cluster Proxmox et constantes partagées.

Ce module est le point d'entrée de la couche d'accès à l'API Proxmox.
Toutes les autres fonctions du package s'appuient sur l'objet ProxmoxAPI
retourné par :func:`connect`.
"""

from proxmoxer import ProxmoxAPI

from ..config import ProxmoxSettings

#: Marqueur injecté dans le champ ``comment`` de chaque pool créé par ce script.
#: Permet de distinguer les pools gérés automatiquement des pools créés manuellement.
POOL_MARKER = "esgilabs-managed"


def connect(settings: ProxmoxSettings) -> ProxmoxAPI:
    """Crée et retourne un client ProxmoxAPI authentifié par token.

    Args:
        settings: Objet :class:`~esgilabs.config.ProxmoxSettings` contenant
            le host, le token ID et le secret.

    Returns:
        Instance ``ProxmoxAPI`` prête à l'emploi.
    """
    user, token_name = settings.token_id.split("!")
    return ProxmoxAPI(
        settings.host,
        user=user,
        token_name=token_name,
        token_value=settings.token_secret,
        verify_ssl=False,
    )

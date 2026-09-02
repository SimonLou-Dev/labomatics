"""Exceptions custom pour l'API Proxmox."""


class ProxmoxAPIError(Exception):
    """Exception de base pour les erreurs API Proxmox."""

    def __init__(
        self, message: str, status_code: int | None = None, response: dict | None = None
    ):
        """Initialise l'exception.

        Args:
            message: Message d'erreur descriptif.
            status_code: Code HTTP de la réponse.
            response: Réponse JSON complète.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response or {}


class ProxmoxAuthError(ProxmoxAPIError):
    """Erreur d'authentification (401, 403)."""

    pass


class ProxmoxNotFoundError(ProxmoxAPIError):
    """Ressource non trouvée (404)."""

    pass


class ProxmoxValidationError(ProxmoxAPIError):
    """Erreur de validation (400)."""

    pass


class ProxmoxConflictError(ProxmoxAPIError):
    """Ressource en conflit (409, ex: existe déjà)."""

    pass


class ProxmoxServerError(ProxmoxAPIError):
    """Erreur serveur (5xx)."""

    pass


class ProxmoxConnectionError(ProxmoxAPIError):
    """Erreur de connexion (timeout, réseau)."""

    pass


class ProxmoxTimeoutError(ProxmoxConnectionError):
    """Timeout API."""

    pass

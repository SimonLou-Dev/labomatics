"""Résumé final de l'installation affiché sur l'écran d'installation."""

from __future__ import annotations

from typing import Any, Mapping, Optional


class FinalSummary:
    """Met en forme le résumé enregistré par la tâche `health`."""

    def __init__(self, data: Optional[Mapping[str, Any]]) -> None:
        """Initialise le résumé.

        Args:
            data: Valeurs de `final_summary` du store, ou None si absentes.
        """
        self.data = data or {}

    def lines(self) -> list[tuple[str, str]]:
        """Construit les lignes du journal.

        Returns:
            Des couples (niveau, texte), vide si aucun résumé n'est disponible.
        """
        if not self.data:
            return []
        return [
            ("ok", "Installation réussie, accès à Labomatics :"),
            ("ok", f"Application : {self.data['frontend_url']}"),
            ("ok", f"API : {self.data['api_url']}"),
            ("ok", f"Keycloak : {self.data['keycloak_url']}"),
            ("ok", f"Identifiant : {self.data['admin_username']}"),
            (
                "warn",
                f"Mot de passe temporaire : {self.data['admin_temp_password']} "
                "(à changer à la première connexion)",
            ),
        ]

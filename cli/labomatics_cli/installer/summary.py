"""Récapitulatif final de l'installation affiché sur l'écran d'installation."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from labomatics_cli.tui import SummarySection


class FinalSummary:
    """Met en forme le résumé enregistré par la tâche `health`."""

    def __init__(self, data: Optional[Mapping[str, Any]]) -> None:
        """Initialise le résumé.

        Args:
            data: Valeurs de `final_summary` du store, ou None si absentes.
        """
        self.data = data or {}

    def sections(self) -> list[SummarySection]:
        """Construit les sections du récapitulatif.

        Returns:
            Les sections Accès et Compte administrateur, vide sans résumé.
        """
        if not self.data:
            return []
        return [
            SummarySection(
                "Accès",
                [
                    ("Application", self.data["frontend_url"]),
                    ("API", self.data["api_url"]),
                    ("Keycloak", self.data["keycloak_url"]),
                ],
            ),
            SummarySection(
                "Compte administrateur",
                [
                    ("Identifiant", self.data["admin_username"]),
                    ("Mot de passe", self.data["admin_temp_password"]),
                ],
                "Mot de passe temporaire : à changer à la première connexion.",
            ),
        ]

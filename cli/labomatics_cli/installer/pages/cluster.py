"""Page 0 : choix du cluster à installer ou à modifier."""

from __future__ import annotations

from typing import Optional, Sequence

from labomatics_cli.tui import SelectField, Step, Wizard

NEW_CLUSTER = "__new__"


class ClusterChoice:
    """Écran de choix entre un nouveau cluster et un cluster existant."""

    def __init__(self, names: Sequence[str]) -> None:
        """Initialise l'écran.

        Args:
            names: Noms des clusters déjà connus.
        """
        self.names = list(names)

    def build_wizard(self) -> Wizard:
        """Construit le mini-assistant de choix.

        Returns:
            Un assistant à une étape, sans récapitulatif.
        """
        options = [(NEW_CLUSTER, "Nouveau cluster")] + [(n, n) for n in self.names]
        step = Step(
            "Cluster",
            [SelectField("Cluster", options, key="cluster", required=True)],
        )
        return Wizard("labomatics install", [step], recap=False)

    def ask(self) -> Optional[str]:
        """Affiche le choix.

        Returns:
            Le nom du cluster choisi, `NEW_CLUSTER` pour un nouveau, ou None si abandonné.
        """
        result = self.build_wizard().run()
        return None if result is None else str(result["cluster"])

from __future__ import annotations

from typing import Any, Callable

from .step import Step
from .theme import LABEL_WIDTH


class Recap:
    """Texte de récapitulatif des valeurs saisies, par étape."""

    def __init__(self, steps: Callable[[], list[Step]]):
        """Initialise le récapitulatif.

        Args:
            steps: Fonction renvoyant les étapes visibles.
        """
        self._steps = steps

    def fragments(self) -> list[Any]:
        """Construit le récapitulatif des champs visibles.

        Returns:
            Les fragments de texte formaté.
        """
        out: list[Any] = []
        for step in self._steps():
            fields = step.visible_fields()
            if not fields:
                continue
            if out:
                out.append(("", "\n"))
            out += [("class:recap-step", step.title), ("", "\n")]
            for field in fields:
                out += [
                    ("class:recap-key", f"  {field.label:<{LABEL_WIDTH - 2}}"),
                    ("class:recap-value", field.display_value()),
                    ("", "\n"),
                ]
        return out

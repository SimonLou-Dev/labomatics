from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class WizardContext:
    """État partagé par toutes les étapes : valeurs des champs visibles et cache libre."""

    values: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    collector: Callable[[], None] | None = field(default=None, init=False, repr=False)

    def refresh(self) -> None:
        """Recalcule `values` via le collecteur de l'assistant, s'il est branché."""
        if self.collector is not None:
            self.collector()

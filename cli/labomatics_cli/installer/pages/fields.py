"""Champs texte avec aide dynamique ou valeur suggérée."""

from __future__ import annotations

from typing import Any, Callable, Optional

from labomatics_cli.tui import TextField, WizardContext

Hint = Callable[[WizardContext], Optional[str]]


class HintField(TextField):
    """Champ texte dont l'aide est calculée à partir des autres champs."""

    def __init__(self, label: str, *, hint: Hint, **kw: Any) -> None:
        """Initialise le champ.

        Args:
            label: Libellé du champ.
            hint: Fonction (contexte) renvoyant l'aide, ou None pour l'aide statique.
            **kw: Options communes de `TextField`.
        """
        super().__init__(label, **kw)
        self.hint = hint

    def _hint_text(self) -> Optional[str]:
        """Texte d'aide courant.

        Returns:
            L'aide dynamique, sinon l'aide statique, sinon None.
        """
        return self.hint(self.ctx) or self.helper

    def _hint_visible(self) -> bool:
        """Indique si la ligne d'aide ou d'erreur est affichée.

        Returns:
            True s'il y a une erreur ou une aide.
        """
        return bool(self.error or self._hint_text())

    def _hint_fragments(self) -> list[Any]:
        """Fragments de la ligne d'aide ou d'erreur.

        Returns:
            Les fragments de texte formaté.
        """
        if self.error:
            return super()._hint_fragments()
        return [("class:helper", self._hint_text() or "")]


class PrefillField(TextField):
    """Champ texte prérempli à partir des autres champs, tant que l'utilisateur ne l'a pas modifié."""

    def __init__(
        self,
        label: str,
        *,
        suggest: Callable[[WizardContext], Optional[str]],
        **kw: Any,
    ) -> None:
        """Initialise le champ.

        Args:
            label: Libellé du champ.
            suggest: Fonction (contexte) renvoyant la valeur à préremplir, ou None.
            **kw: Options communes de `TextField`.
        """
        super().__init__(label, **kw)
        self.suggest = suggest
        self._filled = ""

    def sync(self) -> None:
        """Recopie la suggestion si le champ est vide ou contient encore l'ancien préremplissage."""
        if self.locked:
            return
        text = self.input.text.strip()
        if text and text != self._filled:
            return
        suggestion = self.suggest(self.ctx) or ""
        if suggestion != text:
            self.set_value(suggestion)
        self._filled = suggestion

    def on_enter(self) -> None:
        """Préremplit le champ à l'affichage de l'étape."""
        super().on_enter()
        self.sync()

    def _hint_visible(self) -> bool:
        """Resynchronise le préremplissage à chaque rendu (changement de bridge).

        Returns:
            True s'il y a une erreur ou une aide.
        """
        self.sync()
        return super()._hint_visible()

    @property
    def value(self) -> str:
        """Texte du champ, après synchronisation du préremplissage.

        Returns:
            La valeur effective.
        """
        self.sync()
        return super().value

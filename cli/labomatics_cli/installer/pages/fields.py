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


class SuggestField(HintField):
    """Champ texte qui prend une valeur suggérée tant qu'il reste vide."""

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
            suggest: Fonction (contexte) renvoyant la valeur suggérée, ou None.
            **kw: Options communes de `TextField`.
        """
        self.suggest = suggest
        super().__init__(label, hint=self._suggestion_hint, **kw)

    def _suggestion_hint(self, ctx: WizardContext) -> Optional[str]:
        """Aide indiquant la valeur utilisée si le champ reste vide.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            Le texte d'aide, ou None sans suggestion ou si le champ est rempli.
        """
        suggestion = self.suggest(ctx)
        if suggestion and not self.input.text.strip():
            return f"Laisser vide pour utiliser {suggestion}"
        return None

    @property
    def value(self) -> str:
        """Texte saisi, ou la suggestion si le champ est vide.

        Returns:
            La valeur effective.
        """
        return super().value or (self.suggest(self.ctx) or "")

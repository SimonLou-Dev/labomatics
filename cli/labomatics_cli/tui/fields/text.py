from __future__ import annotations

from typing import Any

from prompt_toolkit.application import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.widgets import TextArea

from .base import Field


class TextField(Field):
    """Saisie d'une ligne de texte, éventuellement masquée."""

    def __init__(self, label: str, *, password: bool = False, **kw: Any):
        """Initialise le champ texte.

        Args:
            label: Libellé affiché devant le champ.
            password: Masque la saisie.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        super().__init__(label, **kw)
        self.password = password
        self.input = TextArea(
            multiline=False,
            height=1,
            password=password,
            accept_handler=self._accept,
        )
        self.input.window.style = lambda: self._box_style(self.input)
        self.input.buffer.on_text_changed += self._on_change
        self._focus = self.input
        self._init_default()

    def _widget(self) -> Any:
        """Zone de saisie.

        Returns:
            Le TextArea.
        """
        return self.input

    @property
    def value(self) -> str:
        """Texte saisi sans espaces autour.

        Returns:
            Le texte nettoyé.
        """
        return self.input.text.strip()

    def set_value(self, value: Any) -> None:
        """Remplace le texte, curseur en fin.

        Args:
            value: Valeur à traiter.
        """
        text = "" if value is None else str(value)
        self.input.buffer.set_document(Document(text, len(text)), bypass_readonly=True)

    def display_value(self) -> str:
        """Texte du récapitulatif (masqué pour un mot de passe).

        Returns:
            La valeur lisible.
        """
        if self.password:
            return "••••••••" if self.value else "—"
        return super().display_value()

    def _on_change(self, _buffer: Any) -> None:
        """Revalide en douceur quand le texte change alors qu'une erreur est affichée.

        Args:
            _buffer: Tampon de saisie (inutilisé).
        """
        if self.error:
            self.validate(soft=True)

    def _accept(self, _buffer: Any) -> bool:
        """Valide la saisie et passe au champ suivant.

        Args:
            _buffer: Tampon de saisie (inutilisé).

        Returns:
            Toujours True pour conserver le texte.
        """
        if self.validate(soft=True):
            get_app().layout.focus_next()
        return True  # garde le texte (sinon Entrée vide le champ)


class PasswordField(TextField):
    """Saisie de texte masquée."""

    def __init__(self, label: str, **kw: Any):
        """Initialise le champ mot de passe.

        Args:
            label: Libellé affiché devant le champ.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        super().__init__(label, password=True, **kw)

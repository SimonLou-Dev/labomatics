from __future__ import annotations

from functools import partial
from typing import Any

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea

from ..theme import LOCK_MARK
from ..widgets import PillButton, is_focused, on_click
from .base import Check, Field

ITEMS_HELP = "↑/↓ choisir · Suppr ou x pour retirer"


class ListField(Field):
    """Liste de textes : saisie, ajout par Entrée ou bouton, retrait au clavier ou à la souris."""

    freezes_widget = False

    def __init__(
        self,
        label: str,
        *,
        item_validator: Check | None = None,
        add_label: str = "Ajouter",
        **kw: Any,
    ):
        """Initialise la liste.

        Args:
            label: Libellé affiché devant le champ.
            item_validator: Validateur de chaque élément, même signature que `validator`.
            add_label: Libellé du bouton d'ajout.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        super().__init__(label, **kw)
        self.items: list[str] = []
        self.item_validator = item_validator
        self.cursor = 0
        self._frozen: set[str] = set()

        self.input = TextArea(multiline=False, height=1, accept_handler=self._accept)
        self.input.window.style = lambda: self._box_style(self.input)
        self.input.buffer.on_text_changed += self._on_change
        self.add_btn = PillButton(f"+ {add_label}", self._add)

        bindings = KeyBindings()

        @bindings.add("up")
        def _(event: Any) -> None:
            """Remonte le curseur dans la liste.

            Args:
                event: Événement de touche.
            """
            self.cursor = max(self.cursor - 1, 0)

        @bindings.add("down")
        def _(event: Any) -> None:
            """Descend le curseur dans la liste.

            Args:
                event: Événement de touche.
            """
            self.cursor = min(self.cursor + 1, len(self.items) - 1)

        @bindings.add("delete")
        @bindings.add("backspace")
        @bindings.add("x")
        def _(event: Any) -> None:
            """Retire l'élément sous le curseur.

            Args:
                event: Événement de touche.
            """
            self._remove(self.cursor)

        self.list_window = Window(
            FormattedTextControl(
                self._render_items,
                focusable=Condition(self._any_removable),
                key_bindings=bindings,
                show_cursor=False,
            ),
        )
        self._items_container = ConditionalContainer(
            self.list_window, filter=Condition(lambda: bool(self.items))
        )
        self._body = HSplit(
            [
                VSplit([self.input, Window(width=1), self.add_btn], height=1),
                self._items_container,
            ]
        )
        self._focus = self.input
        self._init_default()

    @property
    def keys_help(self) -> str:  # type: ignore[override]
        """Aide clavier selon la zone qui a le focus.

        Returns:
            Le texte d'aide du pied de page.
        """
        if self._items_focused():
            return ITEMS_HELP
        return "Entrée ajouter · Tab vers la liste pour retirer"

    def _removable(self, index: int) -> bool:
        """Indique si un élément peut être retiré (les éléments verrouillés non).

        Args:
            index: Indice de l'option ou de l'élément.

        Returns:
            True si retirable.
        """
        return not (self.locked and self.items[index] in self._frozen)

    def _any_removable(self) -> bool:
        """Indique s'il reste au moins un élément retirable.

        Returns:
            True s'il en reste un.
        """
        return any(self._removable(i) for i in range(len(self.items)))

    def _items_focused(self) -> bool:
        """Indique si la liste d'éléments porte le focus.

        Returns:
            True si elle a le focus.
        """
        return bool(self.items) and is_focused(self.list_window)

    def _widget(self) -> Any:
        """Saisie, bouton d'ajout et liste.

        Returns:
            Le conteneur du champ.
        """
        return self._body

    @property
    def value(self) -> list[str]:
        """Éléments de la liste.

        Returns:
            Une copie de la liste.
        """
        return list(self.items)

    def set_value(self, value: Any) -> None:
        """Remplace les éléments ; ils deviennent les éléments verrouillables.

        Args:
            value: Valeur à traiter.
        """
        self.items = [str(v) for v in value or []]
        self._frozen = set(self.items)
        self.cursor = 0

    def display_value(self) -> str:
        """Éléments séparés par des virgules.

        Returns:
            Le texte du récapitulatif.
        """
        return ", ".join(self.items) or "—"

    def validate(self, soft: bool = False) -> bool:
        """Ajoute la saisie en attente puis valide la liste.

        Args:
            soft: Si vrai, n'ajoute pas la saisie en attente.

        Returns:
            True si la liste est valide.
        """
        if not self.visible:
            self.error = None
            return True
        if not soft and self.input.text.strip() and not self._add():
            return False
        return super().validate(soft)

    def _hint_visible(self) -> bool:
        """Indique si la ligne d'aide est affichée.

        Returns:
            True s'il y a une erreur ou une aide.
        """
        return super()._hint_visible() or self._items_focused() or self.locked

    def _hint_fragments(self) -> list[Any]:
        """Fragments de la ligne d'aide ou d'erreur.

        Returns:
            Les fragments de texte formaté.
        """
        if not self.error and self._items_focused():
            return [("class:helper", ITEMS_HELP)]
        if not self.error and self.locked:
            return [("class:locked-mark", f"Éléments existants {LOCK_MARK}")]
        return super()._hint_fragments()

    def _on_change(self, _buffer: Any) -> None:
        """Efface l'erreur dès que la saisie change.

        Args:
            _buffer: Tampon de saisie (inutilisé).
        """
        self.error = None

    def _accept(self, _buffer: Any) -> bool:
        """Ajoute la saisie, ou passe au champ suivant si elle est vide.

        Args:
            _buffer: Tampon de saisie (inutilisé).

        Returns:
            Toujours True pour conserver le texte.
        """
        if self.input.text.strip():
            self._add()
        else:
            get_app().layout.focus_next()
        return True

    def _add(self) -> bool:
        """Valide et ajoute la saisie courante.

        Returns:
            True si rien à ajouter ou ajout réussi.
        """
        text = self.input.text.strip()
        if not text:
            return True
        self.ctx.refresh()
        error = (
            self.item_validator(text, self.ctx.values) if self.item_validator else None
        )
        if error is None and text in self.items:
            error = "Déjà dans la liste"
        if error:
            self.error = error
            return False
        self.items.append(text)
        self.input.text = ""
        self.error = None
        get_app().layout.focus(self.input)
        return True

    def _remove(self, index: int) -> None:
        """Retire un élément s'il est retirable.

        Args:
            index: Indice de l'option ou de l'élément.
        """
        if not 0 <= index < len(self.items) or not self._removable(index):
            return
        del self.items[index]
        self.cursor = min(self.cursor, max(len(self.items) - 1, 0))
        if not self._any_removable() and is_focused(self.list_window):
            get_app().layout.focus(self.input)

    def _select_click(self, index: int) -> None:
        """Place le curseur sur un élément au clic.

        Args:
            index: Indice de l'option ou de l'élément.
        """
        self.cursor = index
        if self._any_removable():
            get_app().layout.focus(self.list_window)

    def _render_items(self) -> list[Any]:
        """Dessine les éléments, avec ✕ pour les retirables.

        Returns:
            Les fragments de texte formaté.
        """
        focused = is_focused(self.list_window)
        out: list[Any] = []
        for i, item in enumerate(self.items):
            if i:
                out.append(("", "\n"))
            current = focused and i == self.cursor
            out.append(
                (
                    "class:item-cursor" if current else "class:item",
                    f" • {item} ",
                    on_click(partial(self._select_click, i)),
                )
            )
            if self._removable(i):
                out.append(
                    ("class:item-remove", " ✕ ", on_click(partial(self._remove, i)))
                )
        return out

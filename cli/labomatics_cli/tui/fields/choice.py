from __future__ import annotations

from functools import partial
from typing import Any, Sequence

from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl

from ..widgets import is_focused, on_click, pill
from .base import Field

EMPTY_TEXT = "Aucune option disponible"


def _normalize(options: Sequence[Any]) -> list[tuple[Any, str]]:
    """Normalise des options en couples (valeur, libellé).

    Args:
        options: Options à normaliser.

    Returns:
        La liste de couples (valeur, libellé).
    """
    return [o if isinstance(o, tuple) else (o, str(o)) for o in options]


class _ChoiceField(Field):
    """Base des champs à choix : gère options statiques ou dynamiques et sélection."""

    window: Window

    def __init__(self, label: str, options: Any, **kw: Any):
        """Initialise le champ à choix.

        Args:
            label: Libellé affiché devant le champ.
            options: Options : valeurs ou couples (valeur, libellé), ou fabrique prenant le contexte.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        super().__init__(label, **kw)
        self._source = options
        self._pending: Any = None
        self.options: list[tuple[Any, str]] = []
        self.index = 0
        if not callable(options):
            self._set_options(options)

    def _set_options(self, options: Sequence[Any]) -> None:
        """Remplace les options en conservant la sélection si possible.

        Args:
            options: Nouvelles options.
        """
        current = self.value
        self.options = _normalize(options)
        values = [v for v, _ in self.options]
        target = self._pending if self._pending in values else current
        self.index = values.index(target) if target in values else 0
        self._options_changed()

    def _options_changed(self) -> None:
        """Hook appelé quand la sélection ou les options changent."""
        pass

    def on_enter(self) -> None:
        """Réévalue les options dynamiques à l'affichage de l'étape."""
        if callable(self._source):
            self._set_options(self._source(self.ctx))

    def choose(self, index: int) -> None:
        """Sélectionne une option par indice (circulaire).

        Args:
            index: Indice de l'option ou de l'élément.
        """
        if self.options:
            self.index = index % len(self.options)
            self._pending = None

    @property
    def value(self) -> Any:
        """Valeur de l'option sélectionnée.

        Returns:
            La valeur, ou None sans option.
        """
        return self.options[self.index][0] if self.options else None

    def set_value(self, value: Any) -> None:
        """Sélectionne l'option de cette valeur (mémorisée si elle n'existe pas encore).

        Args:
            value: Valeur à sélectionner.
        """
        self._pending = value
        values = [v for v, _ in self.options]
        if value in values:
            self.index = values.index(value)
            self._options_changed()

    def display_value(self) -> str:
        """Libellé de l'option sélectionnée.

        Returns:
            Le libellé, ou « — » sans option.
        """
        return self.options[self.index][1] if self.options else "—"

    def _widget(self) -> Any:
        """Fenêtre du champ.

        Returns:
            La fenêtre prompt_toolkit.
        """
        return self.window


class RadioField(_ChoiceField):
    """Choix unique affiché en boutons radio."""

    keys_help = "←/→ choisir"

    def __init__(self, label: str, options: Any, *, inline: bool = True, **kw: Any):
        """Initialise le champ radio.

        Args:
            label: Libellé affiché devant le champ.
            options: Options : valeurs ou couples (valeur, libellé), ou fabrique prenant le contexte.
            inline: Affiche les options sur une ligne.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        super().__init__(label, options, **kw)
        self.inline = inline
        bindings = KeyBindings()

        @bindings.add("left")
        @bindings.add("up")
        def _(event: Any) -> None:
            """Sélectionne l'option précédente.

            Args:
                event: Événement de touche.
            """
            self.choose(self.index - 1)

        @bindings.add("right")
        @bindings.add("down")
        @bindings.add(" ")
        def _(event: Any) -> None:
            """Sélectionne l'option suivante.

            Args:
                event: Événement de touche.
            """
            self.choose(self.index + 1)

        bindings.add("enter")(focus_next)
        self.window = Window(
            FormattedTextControl(
                self._render, focusable=True, key_bindings=bindings, show_cursor=False
            )
        )
        self._focus = self.window
        self._init_default()

    def _select(self, index: int) -> None:
        """Sélectionne une option au clic et prend le focus.

        Args:
            index: Indice de l'option ou de l'élément.
        """
        self.choose(index)
        get_app().layout.focus(self.window)

    def _render(self) -> list[Any]:
        """Dessine les options.

        Returns:
            Les fragments de texte formaté.
        """
        if not self.options:
            return [("class:helper", EMPTY_TEXT)]
        focused = is_focused(self.window)
        sep = "   " if self.inline else "\n"
        out: list[Any] = []
        for i, (_, text) in enumerate(self.options):
            if i:
                out.append(("", sep))
            on = i == self.index
            cls = "class:radio-on" if on else "class:radio-off"
            if on and focused:
                cls += " underline"
            out.append(
                (
                    cls,
                    f"{'◉' if on else '○'} {text}",
                    on_click(partial(self._select, i)),
                )
            )
        return out


class SelectField(_ChoiceField):
    """Liste déroulante à choix unique."""

    keys_help = "Entrée ouvrir · ↑/↓ choisir · Échap fermer"

    def __init__(self, label: str, options: Any, **kw: Any):
        """Initialise la liste déroulante.

        Args:
            label: Libellé affiché devant le champ.
            options: Options : valeurs ou couples (valeur, libellé), ou fabrique prenant le contexte.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        super().__init__(label, options, **kw)
        self.cursor = self.index
        self.open = False
        bindings = KeyBindings()

        @bindings.add("enter")
        @bindings.add(" ")
        def _(event: Any) -> None:
            """Ouvre la liste, ou valide l'option sous le curseur.

            Args:
                event: Événement de touche.
            """
            if self.open:
                self.choose(self.cursor)
                self.open = False
            else:
                self._open()

        @bindings.add("down")
        def _(event: Any) -> None:
            """Ouvre la liste, ou descend le curseur.

            Args:
                event: Événement de touche.
            """
            if self.open:
                self.cursor = min(self.cursor + 1, len(self.options) - 1)
            else:
                self._open()

        @bindings.add("up")
        def _(event: Any) -> None:
            """Remonte le curseur.

            Args:
                event: Événement de touche.
            """
            if self.open:
                self.cursor = max(self.cursor - 1, 0)

        @bindings.add("escape", eager=True)
        def _(event: Any) -> None:
            """Ferme la liste sans changer la sélection.

            Args:
                event: Événement de touche.
            """
            self.open = False

        self.window = Window(
            FormattedTextControl(
                self._render, focusable=True, key_bindings=bindings, show_cursor=False
            ),
            width=self._width,
            dont_extend_width=True,
        )
        self._focus = self.window
        self._init_default()

    def _options_changed(self) -> None:
        """Replace le curseur sur la sélection."""
        self.cursor = self.index

    def _open(self) -> None:
        """Ouvre la liste si elle a des options."""
        if self.options:
            self.cursor = self.index
            self.open = True

    def _toggle_click(self) -> None:
        """Ouvre ou ferme la liste au clic."""
        get_app().layout.focus(self.window)
        if self.open:
            self.open = False
        else:
            self._open()

    def _choose_click(self, index: int) -> None:
        """Choisit une option au clic et ferme la liste.

        Args:
            index: Indice de l'option ou de l'élément.
        """
        self.choose(index)
        self.open = False

    def _width(self) -> int:
        """Largeur de la boîte selon l'option la plus longue.

        Returns:
            La largeur en colonnes.
        """
        return max([len(t) for _, t in self.options] + [len(EMPTY_TEXT)]) + 6

    def _render(self) -> list[Any]:
        """Dessine la boîte et, si ouverte, la liste.

        Returns:
            Les fragments de texte formaté.
        """
        if not is_focused(self.window):
            self.open = False
        width = self._width()
        box = self._box_style(self.window)
        toggle = on_click(self._toggle_click)
        out: list[Any] = [
            (
                box,
                f"  {self.display_value() if self.options else EMPTY_TEXT}".ljust(
                    width - 2
                ),
                toggle,
            ),
            (box, "▴ " if self.open else "▾ ", toggle),
        ]
        if self.open:
            for i, (_, text) in enumerate(self.options):
                cls = "class:item-cursor" if i == self.cursor else "class:item"
                mark = "✓" if i == self.index else " "
                out += [
                    ("", "\n"),
                    (
                        cls,
                        f" {mark} {text}".ljust(width),
                        on_click(partial(self._choose_click, i)),
                    ),
                ]
        return out


class ConfirmField(Field):
    """Choix Oui/Non sous forme de deux boutons."""

    keys_help = "←/→ Oui/Non"

    def __init__(self, label: str, *, yes: str = "Oui", no: str = "Non", **kw: Any):
        """Initialise le champ de confirmation (Oui par défaut).

        Args:
            label: Libellé affiché devant le champ.
            yes: Libellé de la réponse positive.
            no: Libellé de la réponse négative.
            **kw: Options communes de `Field` (key, helper, validator, required, default, visible_if, locked).
        """
        kw.setdefault("default", True)
        super().__init__(label, **kw)
        self.checked = True
        self.yes, self.no = yes, no
        bindings = KeyBindings()

        @bindings.add("left")
        @bindings.add("right")
        @bindings.add(" ")
        def _(event: Any) -> None:
            """Inverse la réponse.

            Args:
                event: Événement de touche.
            """
            self.checked = not self.checked

        @bindings.add("o")
        def _(event: Any) -> None:
            """Répond Oui.

            Args:
                event: Événement de touche.
            """
            self.checked = True

        @bindings.add("n")
        def _(event: Any) -> None:
            """Répond Non.

            Args:
                event: Événement de touche.
            """
            self.checked = False

        bindings.add("enter")(focus_next)
        self.window = Window(
            FormattedTextControl(
                self._render, focusable=True, key_bindings=bindings, show_cursor=False
            ),
            height=1,
        )
        self._focus = self.window
        self._init_default()

    def _set(self, value: bool) -> None:
        """Fixe la réponse au clic et prend le focus.

        Args:
            value: Réponse (True pour Oui).
        """
        self.checked = value
        get_app().layout.focus(self.window)

    def _render(self) -> list[Any]:
        """Dessine les deux boutons.

        Returns:
            Les fragments de texte formaté.
        """
        return (
            pill(self.yes, self.checked, on_click(partial(self._set, True)))
            + [("", "  ")]
            + pill(self.no, not self.checked, on_click(partial(self._set, False)))
        )

    def _widget(self) -> Any:
        """Fenêtre du champ.

        Returns:
            La fenêtre prompt_toolkit.
        """
        return self.window

    @property
    def value(self) -> bool:
        """Réponse courante.

        Returns:
            True pour Oui, False pour Non.
        """
        return self.checked

    def set_value(self, value: Any) -> None:
        """Fixe la réponse.

        Args:
            value: Réponse (True pour Oui).
        """
        self.checked = bool(value)

    def is_empty(self) -> bool:
        """Une confirmation n'est jamais vide.

        Returns:
            Toujours False.
        """
        return False

    def display_value(self) -> str:
        """Libellé de la réponse.

        Returns:
            Le libellé Oui ou Non.
        """
        return self.yes if self.checked else self.no

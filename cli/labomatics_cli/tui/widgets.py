from __future__ import annotations

import asyncio
from typing import Any, Callable

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEventType

from .theme import CAP_LEFT, CAP_RIGHT, SPINNER_FRAMES


def is_focused(target: Any) -> bool:
    """Indique si un élément de la mise en page a le focus.

    Args:
        target: Élément dont on teste le focus.

    Returns:
        True si l'élément a le focus.
    """
    return get_app().layout.has_focus(target)


def on_click(action: Callable[[], object]) -> Callable[[Any], Any]:
    """Fabrique un gestionnaire de souris déclenché au relâchement du clic.

    Args:
        action: Action déclenchée au clic.

    Returns:
        Le gestionnaire prompt_toolkit.
    """

    def handler(mouse_event: Any) -> Any:
        """Exécute l'action au relâchement du bouton.

        Args:
            mouse_event: Événement souris.

        Returns:
            None si traité, NotImplemented sinon.
        """
        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return NotImplemented
        action()
        return None

    return handler


def pill(text: str, on: bool, handler: Callable[[Any], Any] | None = None) -> list[Any]:
    """Dessine un bouton en pilule avec capuchons Nerd Font.

    Args:
        text: Texte du bouton.
        on: Style actif.
        handler: Gestionnaire de souris, ou None.

    Returns:
        Les fragments de texte formaté.
    """
    state = "on" if on else "off"
    fragments = [
        (f"class:pill-{state}-cap", CAP_LEFT),
        (f"class:pill-{state}", f" {text} "),
        (f"class:pill-{state}-cap", CAP_RIGHT),
    ]
    return (
        [(style, content, handler) for style, content in fragments]
        if handler
        else fragments
    )


class PillButton:
    """Bouton en pilule focalisable (Entrée, espace ou clic)."""

    def __init__(self, text: str, handler: Callable[[], object]):
        """Initialise le bouton.

        Args:
            text: Texte du bouton.
            handler: Action déclenchée.
        """
        self.text = text
        self.handler = handler
        bindings = KeyBindings()

        @bindings.add("enter")
        @bindings.add(" ")
        def _(event: Any) -> None:
            """Déclenche l'action du bouton.

            Args:
                event: Événement de touche.
            """
            handler()

        self.window = Window(
            FormattedTextControl(
                lambda: pill(self.text, is_focused(self), on_click(self._click)),
                focusable=True,
                key_bindings=bindings,
                show_cursor=False,
            ),
            width=lambda: len(self.text) + 4,
            height=1,
            dont_extend_width=True,
        )

    def _click(self) -> None:
        """Donne le focus au bouton puis déclenche l'action."""
        get_app().layout.focus(self.window)
        self.handler()

    def __pt_container__(self) -> Window:
        """Fenêtre du bouton.

        Returns:
            La fenêtre prompt_toolkit.
        """
        return self.window


class Spinner:
    """Animation d'attente partagée par les écrans de chargement."""

    def __init__(self) -> None:
        """Initialise le compteur d'images."""
        self.frame = 0
        self._task: asyncio.Future[Any] | None = None

    @property
    def glyph(self) -> str:
        """Image courante de l'animation.

        Returns:
            Le caractère à afficher.
        """
        return SPINNER_FRAMES[self.frame % len(SPINNER_FRAMES)]

    def start(self, app: Application[Any], active: Callable[[], bool]) -> None:
        """Lance l'animation en tâche de fond (sans doublon).

        Args:
            app: Application à invalider.
            active: Condition qui maintient l'animation.
        """
        if self._task is None or self._task.done():
            self._task = app.create_background_task(self._run(app, active))

    async def _run(self, app: Application[Any], active: Callable[[], bool]) -> None:
        """Avance l'animation tant que `active` est vrai.

        Args:
            app: Application à invalider.
            active: Condition qui maintient l'animation.
        """
        while active():
            self.frame += 1
            app.invalidate()
            await asyncio.sleep(0.08)
        app.invalidate()


class Busy:
    """Indicateur focusable qui avale toutes les touches sauf Ctrl+C."""

    def __init__(self, spinner: Spinner, text: Callable[[], str]):
        """Initialise l'indicateur.

        Args:
            spinner: Animation partagée.
            text: Fonction renvoyant le texte affiché.
        """
        bindings = KeyBindings()

        @bindings.add(Keys.Any)
        def _(event: Any) -> None:
            """Quitte sur Ctrl+C, ignore les autres touches.

            Args:
                event: Événement de touche.
            """
            if event.key_sequence[0].key == Keys.ControlC:
                event.app.exit(result=None)

        self.window = Window(
            FormattedTextControl(
                lambda: [
                    ("class:spinner", f"{spinner.glyph} "),
                    ("class:step", text()),
                ],
                focusable=True,
                key_bindings=bindings,
                show_cursor=False,
            ),
            height=1,
        )

    def __pt_container__(self) -> Window:
        """Fenêtre de l'indicateur.

        Returns:
            La fenêtre prompt_toolkit.
        """
        return self.window

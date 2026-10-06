"""Outils de test : pilotage d'un Wizard avec des frappes espacées dans un terminal virtuel."""

import asyncio
import io
import time
from typing import Any, Callable

from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output.vt100 import Vt100_Output

TAB, STAB, ENTER = "\t", "\x1b[Z", "\r"
UP, DOWN, LEFT, RIGHT = "\x1b[A", "\x1b[B", "\x1b[D", "\x1b[C"
DELETE, CTRL_U, CTRL_C = "\x1b[3~", "\x15", "\x03"


class WaitUntil:
    """Attend qu'une condition devienne vraie."""

    def __init__(self, cond: Callable[[], bool], timeout: float = 10.0):
        """Mémorise la condition et le délai maximal."""
        self.cond, self.timeout = cond, timeout


def check(cond: Callable[[], bool], msg: str) -> Callable[[], None]:
    """Crée une étape de feed qui vérifie une condition."""

    def _() -> None:
        """Vérifie la condition."""
        assert cond(), msg

    return _


def screen_lines(wizard: Any) -> list[str]:
    """Lignes de texte du dernier écran rendu."""
    screen = wizard.app.renderer._last_screen
    return [
        "".join(screen.data_buffer[y][x].char for x in range(screen.width)).rstrip()
        for y in range(screen.height)
    ]


def on_screen(wizard: Any, text: str) -> bool:
    """Vrai si le texte apparaît sur l'écran."""
    return any(text in line for line in screen_lines(wizard))


def find_chars(wizard: Any, char: str) -> list[tuple[int, int]]:
    """Positions (x, y) d'un caractère à l'écran."""
    screen = wizard.app.renderer._last_screen
    return [
        (x, y)
        for y in range(screen.height)
        for x in range(screen.width)
        if screen.data_buffer[y][x].char == char
    ]


def focused(wizard: Any, target: Any) -> bool:
    """Vrai si l'élément (champ ou widget) a le focus."""
    return wizard.app.layout.has_focus(getattr(target, "_focus", None) or target)


async def drive(
    wizard: Any, feed: list[Any], rows: int = 40, columns: int = 110
) -> tuple[Any, str]:
    """Rejoue `feed` par paquets espacés de 50 ms ; renvoie (résultat, sortie brute)."""
    buf = io.StringIO()
    out = Vt100_Output(
        buf, lambda: Size(rows=rows, columns=columns), term="xterm-256color"
    )
    with create_pipe_input() as inp:
        app = wizard.build_app(input=inp, output=out)

        async def run_feed() -> None:
            """Joue le feed et arrête l'application en cas d'erreur."""
            try:
                await play()
                await asyncio.sleep(1)
                assert not app.is_running, "l'application tourne encore après le feed"
            except BaseException:
                if app.is_running:
                    app.exit(result=None)
                raise

        async def play() -> None:
            """Joue chaque élément du feed."""
            for item in feed:
                await asyncio.sleep(0.05)
                if isinstance(item, WaitUntil):
                    deadline = time.monotonic() + item.timeout
                    while not item.cond():
                        assert time.monotonic() < deadline, "délai dépassé"
                        await asyncio.sleep(0.05)
                elif callable(item):
                    text = item()
                    if isinstance(text, str):
                        inp.send_text(text)
                else:
                    inp.send_text(item)

        task = asyncio.ensure_future(run_feed())
        result = await asyncio.wait_for(app.run_async(), 60)
        await task
    return result, buf.getvalue()


def run(wizard: Any, feed: list[Any], **kw: Any) -> tuple[Any, str]:
    """Version synchrone de `drive`."""
    return asyncio.run(drive(wizard, feed, **kw))

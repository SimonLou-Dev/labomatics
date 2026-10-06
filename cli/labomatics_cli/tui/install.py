from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import ConditionalContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from .theme import BLOCK_WIDTH, LOG_SYMBOLS
from .widgets import Busy, PillButton, Spinner

PENDING, RUNNING, DONE, SKIPPED, FAILED = (
    "pending",
    "running",
    "done",
    "skipped",
    "failed",
)
InstallHandler = Callable[[dict, "InstallReporter"], Awaitable[None]]


@dataclass
class LogLine:
    """Ligne de journal d'installation."""

    time: str
    level: str
    text: str


class InstallReporter:
    """Suit les phases et le journal d'une installation."""

    def __init__(
        self,
        steps: list[str] | tuple[str, ...] = (),
        on_change: Callable[[], None] | None = None,
    ):
        """Initialise le rapporteur.

        Args:
            steps: Noms des phases.
            on_change: Rappel appelé à chaque changement d'état.
        """
        self.steps = list(steps) or ["Installation"]
        self.status = [PENDING] * len(self.steps)
        self.current = -1
        self.failed = False
        self.lines: list[LogLine] = []
        self._on_change = on_change or (lambda: None)
        if not steps:
            self.step(0)

    @property
    def total(self) -> int:
        """Nombre de phases.

        Returns:
            Le nombre de phases.
        """
        return len(self.steps)

    def _index(self, step: int | str) -> int:
        """Convertit un nom ou un indice de phase en indice.

        Args:
            step: Nom ou indice de la phase.

        Returns:
            L'indice de la phase.

        Raises:
            ValueError: Si le nom de phase est inconnu.
        """
        return self.steps.index(step) if isinstance(step, str) else step

    def step(self, step: int | str) -> None:
        """Démarre une phase ; les phases en cours passent à terminé.

        Args:
            step: Nom ou indice de la phase.

        Raises:
            ValueError: Si le nom de phase est inconnu.
        """
        index = self._index(step)
        self.status = [DONE if s == RUNNING else s for s in self.status]
        self.status[index] = RUNNING
        self.current = index
        self._on_change()

    def mark_done(self, step: int | str) -> None:
        """Marque une phase comme déjà terminée (reprise).

        Args:
            step: Nom ou indice de la phase.
        """
        index = self._index(step)
        self.status[index] = DONE
        self.current = max(self.current, index)
        self._on_change()

    def skip(self, step: int | str, reason: str | None = None) -> None:
        """Marque une phase comme ignorée et le consigne dans le journal.

        Args:
            step: Nom ou indice de la phase.
            reason: Motif de l'omission, ajouté au journal.
        """
        index = self._index(step)
        self.status[index] = SKIPPED
        self.current = max(self.current, index)
        suffix = f" ({reason})" if reason else ""
        self.log(f"{self.steps[index]} : ignoré{suffix}")

    def log(self, line: str, level: str = "info") -> None:
        """Ajoute une ligne horodatée au journal.

        Args:
            line: Texte de la ligne.
            level: Niveau : info, ok, warn ou error.
        """
        self.lines.append(LogLine(datetime.now().strftime("%H:%M:%S"), level, line))
        self._on_change()

    def fail(self, message: str) -> None:
        """Marque la phase en cours en échec et consigne l'erreur.

        Args:
            message: Message d'erreur à consigner.
        """
        running = [i for i, s in enumerate(self.status) if s == RUNNING]
        index = running[-1] if running else max(self.current, 0)
        self.status[index] = FAILED
        self.current = index
        self.failed = True
        self.log(message, "error")

    def complete(self) -> None:
        """Termine toutes les phases non ignorées."""
        self.status = [s if s == SKIPPED else DONE for s in self.status]
        self.current = self.total - 1
        self._on_change()

    def label(self) -> str:
        """Libellé « Étape x/n — nom » de la phase courante.

        Returns:
            Le libellé, ou « Échec à l'étape … » en cas d'échec.
        """
        index = min(max(self.current, 0), self.total - 1)
        prefix = "Échec à l'étape" if self.failed else "Étape"
        return f"{prefix} {index + 1}/{self.total} — {self.steps[index]}"


class InstallScreen:
    """Écran d'installation : barre de segments, libellé, journal coloré et bouton Quitter."""

    def __init__(
        self,
        reporter: InstallReporter,
        spinner: Spinner,
        size: Callable[[], tuple[int, int]],
        on_quit: Callable[[], object],
    ):
        """Initialise l'écran.

        Args:
            reporter: Rapporteur d'installation.
            spinner: Animation partagée.
            size: Fonction renvoyant (lignes, colonnes) du terminal.
            on_quit: Action du bouton Quitter.
        """
        self.reporter = reporter
        self.spinner = spinner
        self._size = size
        self.done = False
        self.busy = Busy(spinner, lambda: "Installation en cours…")
        self.quit_btn = PillButton("Quitter", on_quit)
        finished = Condition(lambda: self.done)
        self.container = HSplit(
            [
                Window(FormattedTextControl(self._bar), height=1),
                Window(FormattedTextControl(self._label), height=1),
                Window(height=1),
                Window(FormattedTextControl(self._logs), height=self._log_height),
                Window(height=1),
                ConditionalContainer(self.busy, filter=~finished),
                ConditionalContainer(
                    VSplit(
                        [Window(FormattedTextControl(self._status)), self.quit_btn],
                        height=1,
                    ),
                    filter=finished,
                ),
            ]
        )

    @property
    def succeeded(self) -> bool:
        """Indique si l'installation s'est terminée sans erreur.

        Returns:
            True si terminée sans échec.
        """
        return self.done and not self.reporter.failed

    async def run(self, handler: InstallHandler, values: dict) -> bool:
        """Exécute le gestionnaire d'installation et enregistre son issue.

        Args:
            handler: Coroutine d'installation (valeurs, rapporteur).
            values: Valeurs transmises au gestionnaire.

        Returns:
            True si l'installation a réussi.
        """
        try:
            await handler(values, self.reporter)
        except Exception as exc:
            self.reporter.fail(str(exc) or type(exc).__name__)
        else:
            self.reporter.complete()
        self.done = True
        return self.succeeded

    def _bar(self) -> list[Any]:
        """Dessine la barre de segments (un par phase).

        Returns:
            Les fragments de texte formaté.
        """
        columns = self._size()[1]
        count = self.reporter.total
        width = max(count * 3, min(BLOCK_WIDTH, columns))
        seg = (width - (count - 1)) // count
        out: list[Any] = []
        for i, status in enumerate(self.reporter.status):
            if i:
                out.append(("", " "))
            if status == DONE:
                out.append(("class:bar-on", "█" * seg))
            elif status == SKIPPED:
                out.append(("class:bar-skip", "░" * seg))
            elif status == FAILED:
                out.append(("class:bar-fail", "█" * seg))
            elif status == RUNNING:
                head = self.spinner.frame % (seg + 1)
                out += [
                    ("class:bar-on", "█" * head),
                    ("class:bar-current", "▒" * (seg - head)),
                ]
            else:
                out.append(("class:bar-off", "█" * seg))
        return out

    def _label(self) -> list[Any]:
        """Libellé de la phase courante.

        Returns:
            Les fragments de texte formaté.
        """
        style = "class:error" if self.reporter.failed else "class:step"
        return [(style, self.reporter.label())]

    def _log_height(self) -> int:
        """Hauteur de la zone de journal selon le terminal.

        Returns:
            La hauteur en lignes.
        """
        return max(6, min(16, self._size()[0] - 14))

    def _logs(self) -> list[Any]:
        """Dessine le journal horodaté et coloré.

        Returns:
            Les fragments de texte formaté.
        """
        out: list[Any] = []
        for i, line in enumerate(self.reporter.lines):
            if i:
                out.append(("", "\n"))
            symbol = LOG_SYMBOLS.get(line.level, "·")
            out += [
                ("class:log-time", f"{line.time} "),
                (f"class:log-{line.level}", f"{symbol} {line.text}"),
            ]
        out.append(
            ("[SetCursorPosition]", "")
        )  # fait défiler la fenêtre jusqu'à la dernière ligne
        return out

    def _status(self) -> list[Any]:
        """Message final de succès ou d'échec.

        Returns:
            Les fragments de texte formaté.
        """
        if self.reporter.failed:
            return [("class:error", "✗ L'installation a échoué (voir les logs)")]
        return [("class:title", "Installation terminée ✓")]

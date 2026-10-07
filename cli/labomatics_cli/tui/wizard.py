from __future__ import annotations

from typing import Any, Callable, Collection, Mapping, Sequence

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    Layout,
    ScrollablePane,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.output.color_depth import ColorDepth

from .context import WizardContext
from .fields.base import Field
from .install import InstallHandler, InstallReporter, InstallScreen
from .recap import Recap
from .step import Step
from .theme import BLOCK_WIDTH, STYLE
from .widgets import Busy, PillButton, Spinner


class Wizard:
    """Assistant plein écran : étapes de formulaire, récapitulatif puis écran d'installation."""

    def __init__(
        self,
        title: str,
        steps: Sequence[Step],
        *,
        recap: bool = True,
        initial_values: Mapping[str, Any] | None = None,
        locked_keys: Collection[str] | None = None,
        start_step: int = 0,
        on_step_saved: Callable[[Step, WizardContext], None] | None = None,
        install_steps: Sequence[str] | None = None,
        on_install: InstallHandler | None = None,
        context: WizardContext | None = None,
    ):
        """Construit l'assistant.

        Args:
            title: Titre affiché en haut de l'écran.
            steps: Étapes du formulaire, dans l'ordre.
            recap: Ajoute une étape finale de récapitulatif.
            initial_values: Valeurs de préremplissage, par clé de champ.
            locked_keys: Clés des champs à verrouiller (mode modification).
            start_step: Indice de la première étape affichée (reprise).
            on_step_saved: Callback appelé après chaque étape validée, avant d'avancer.
            install_steps: Noms des phases de l'écran d'installation.
            on_install: Coroutine d'installation, reçoit les valeurs et un InstallReporter.
            context: Contexte partagé ; un nouveau est créé par défaut.
        """
        self.title = title
        self.ctx = context or WizardContext()
        self.ctx.collector = self.collect
        self.recap_step = Step("Récapitulatif", [])
        self.steps = list(steps) + ([self.recap_step] if recap else [])
        self.on_step_saved = on_step_saved
        self.on_install = on_install
        self.app: Application[Any] | None = None
        self.mode = "form"
        self.loading = False
        self.step_error: str | None = None
        self.install_result: dict[str, Any] | None = None
        self.spinner = Spinner()
        self.reporter = InstallReporter(list(install_steps or []), self._invalidate)
        self._visible: list[int] = []

        for step in self.steps:
            step.attach(self.ctx, dict(initial_values or {}), set(locked_keys or ()))
        self.collect()
        self.index = self._clamp(start_step)
        self.current.enter()
        self.collect()

        self.prev_btn = PillButton("Précédent", self.prev)
        self.next_btn = PillButton(self._next_label(), self.next)
        self.install = InstallScreen(
            self.reporter, self.spinner, self._size, self._quit
        )
        self.submit_busy = Busy(self.spinner, lambda: self.current.loading_text)
        self.root = self._build_layout()

    @property
    def current(self) -> Step:
        """Étape actuellement affichée."""
        return self.steps[self.index]

    @property
    def busy(self) -> bool:
        """Vrai pendant une vérification ou une installation en cours."""
        return self.loading or (self.mode == "install" and not self.install.done)

    def collect(self) -> None:
        """Recalcule les étapes visibles et `ctx.values` depuis les champs visibles."""
        self.ctx.values.clear()
        self._visible = []
        for i, step in enumerate(self.steps):
            if step.visible_if is not None and not step.visible_if(self.ctx):
                continue
            self._visible.append(i)
            for field in step.fields:
                if field.visible:
                    self.ctx.values[field.key] = field.value

    def values(self) -> dict[str, Any]:
        """Renvoie une copie des valeurs des champs visibles."""
        self.collect()
        return dict(self.ctx.values)

    def _clamp(self, index: int) -> int:
        """Ramène un indice d'étape sur l'étape visible la plus proche.

        Args:
            index: Indice d'étape souhaité.

        Returns:
            L'indice de l'étape visible la plus proche.
        """
        after = [i for i in self._visible if i >= index]
        return after[0] if after else self._visible[-1]

    def _neighbor(self, step: int) -> int | None:
        """Indice de l'étape visible voisine (+1 suivante, -1 précédente), ou None.

        Args:
            step: +1 pour la suivante, -1 pour la précédente.

        Returns:
            L'indice de l'étape voisine, ou None.
        """
        candidates = [i for i in self._visible if (i - self.index) * step > 0]
        if not candidates:
            return None
        return min(candidates) if step > 0 else max(candidates)

    def _next_label(self) -> str:
        """Libellé du bouton principal selon la position."""
        return "Suivant" if self._neighbor(1) is not None else "Terminer"

    def _invalidate(self) -> None:
        """Demande un nouveau rendu si l'application tourne."""
        if self.app is not None:
            self.app.invalidate()

    def _size(self) -> tuple[int, int]:
        """Taille du terminal (lignes, colonnes)."""
        if self.app is None:
            return 24, 80
        size = self.app.output.get_size()
        return size.rows, size.columns

    def _quit(self) -> None:
        """Quitte depuis l'écran d'installation avec le résultat courant."""
        assert self.app is not None
        self.app.exit(result=self.install_result)

    def _build_layout(self) -> HSplit:
        """Assemble l'en-tête, le corps centré et le pied d'aide."""
        recap_window = Window(
            FormattedTextControl(
                Recap(lambda: [self.steps[i] for i in self._visible]).fragments
            )
        )
        buttons = VSplit(
            [
                Window(),
                ConditionalContainer(
                    VSplit([self.prev_btn, Window(width=2)]),
                    filter=Condition(lambda: self._neighbor(-1) is not None),
                ),
                self.next_btn,
            ],
            height=1,
        )
        error_line = Window(
            FormattedTextControl(lambda: [("class:error", f"✗ {self.step_error}")]),
            height=1,
        )
        form_body = HSplit(
            [
                DynamicContainer(lambda: self.current.container or recap_window),
                Window(height=1),
                ConditionalContainer(
                    error_line, filter=Condition(lambda: bool(self.step_error))
                ),
                ConditionalContainer(
                    buttons, filter=Condition(lambda: not self.loading)
                ),
                ConditionalContainer(
                    self.submit_busy, filter=Condition(lambda: self.loading)
                ),
            ]
        )
        body = DynamicContainer(
            lambda: self.install.container if self.mode == "install" else form_body
        )
        # Les espaceurs se partagent la hauteur libre : corps centré, ou collé en haut s'il déborde
        centered = HSplit(
            [
                Window(),
                VSplit(
                    [
                        Window(),
                        HSplit([body], width=D(preferred=BLOCK_WIDTH, max=BLOCK_WIDTH)),
                        Window(),
                    ]
                ),
                Window(),
            ]
        )
        return HSplit(
            [
                Window(height=1),
                Window(
                    FormattedTextControl([("class:title", self.title)]),
                    height=1,
                    align=WindowAlign.CENTER,
                ),
                Window(
                    FormattedTextControl(self._step_text),
                    height=1,
                    align=WindowAlign.CENTER,
                ),
                Window(height=1),
                ScrollablePane(centered, show_scrollbar=False),
                Window(
                    FormattedTextControl(self._help), height=1, align=WindowAlign.RIGHT
                ),
            ]
        )

    def _step_text(self) -> list[Any]:
        """Texte « Étape x/n — titre » (numérotation sur les étapes visibles)."""
        self.collect()
        if self.mode == "install":
            return [("class:step", "Installation")]
        position = (
            self._visible.index(self.index) + 1 if self.index in self._visible else 1
        )
        return [
            (
                "class:step",
                f"Étape {position}/{len(self._visible)} — {self.current.title}",
            )
        ]

    def _help(self) -> list[Any]:
        """Aide contextuelle affichée en bas à droite."""
        if self.busy:
            parts = ["Ctrl+C quitter"]
        elif self.mode == "install":
            parts = ["Entrée quitter", "Ctrl+C quitter"]
        else:
            field = self.focused_field()
            parts = [field.keys_help] if field else ["Entrée valider"]
            parts += ["Tab/Shift+Tab naviguer", "Ctrl+C quitter"]
        return [("class:help", " · ".join(parts) + "  ")]

    def focused_field(self) -> Field | None:
        """Champ qui porte actuellement le focus, s'il y en a un."""
        return next((f for f in self.current.visible_fields() if f.has_focus()), None)

    def _first_focus(self) -> Any:
        """Premier élément focalisable de l'étape courante."""
        return self.current.first_focus() or self.next_btn

    def _go(self, index: int) -> None:
        """Affiche l'étape `index` (reconstruite si dynamique) et lui donne le focus.

        Args:
            index: Indice absolu de l'étape à afficher.
        """
        assert self.app is not None
        self.index = index
        self.step_error = None
        self.current.enter()
        self.collect()
        self.next_btn.text = self._next_label()
        self.app.layout.focus(self._first_focus())

    def next(self) -> None:
        """Valide l'étape courante puis lance sa soumission ou avance."""
        assert self.app is not None
        step = self.current
        self.step_error = None
        if not step.validate():
            error_field = step.first_error()
            if error_field is not None and error_field.focus_target is not None:
                self.app.layout.focus(error_field.focus_target)
            return
        if step.on_submit:
            self._start_submit(step)
        else:
            self._finish_step(step)

    def prev(self) -> None:
        """Revient à l'étape visible précédente."""
        previous = self._neighbor(-1)
        if previous is not None:
            self._go(previous)

    def _finish_step(self, step: Step) -> None:
        """Appelle le hook de sauvegarde puis avance ; une erreur reste sur l'étape.

        Args:
            step: Étape qui vient d'être validée.
        """
        assert self.app is not None
        if self.on_step_saved is not None and step is not self.recap_step:
            try:
                self.on_step_saved(step, self.ctx)
            except Exception as exc:
                self.step_error = str(exc) or type(exc).__name__
                self.app.layout.focus(self.next_btn)
                return
        self._advance()

    def _advance(self) -> None:
        """Passe à l'étape suivante, ou lance l'installation, ou termine."""
        following = self._neighbor(1)
        if following is not None:
            self._go(following)
        elif self.on_install:
            self._start_install()
        else:
            assert self.app is not None
            self.app.exit(result=self.values())

    def _start_submit(self, step: Step) -> None:
        """Lance `on_submit` en tâche de fond avec un indicateur d'attente.

        Args:
            step: Étape dont `on_submit` est lancé.
        """
        assert self.app is not None
        self.loading = True
        self.app.layout.focus(self.submit_busy)
        self.app.create_background_task(self._run_submit(step))
        self.spinner.start(self.app, lambda: self.busy)

    async def _run_submit(self, step: Step) -> None:
        """Exécute `on_submit` et traite son résultat (erreur ou suite).

        Args:
            step: Étape dont `on_submit` est exécuté.
        """
        assert self.app is not None and step.on_submit is not None
        try:
            error = await step.on_submit(self.ctx)
        except Exception as exc:
            error = str(exc) or type(exc).__name__
        self.loading = False
        if error:
            self.step_error = error
            self.app.layout.focus(self.next_btn)
        else:
            self._finish_step(step)
        self._invalidate()

    def _start_install(self) -> None:
        """Bascule sur l'écran d'installation et lance `on_install`."""
        assert self.app is not None
        self.mode = "install"
        self.app.layout.focus(self.install.busy)
        self.app.create_background_task(self._run_install())
        self.spinner.start(self.app, lambda: self.busy)

    async def _run_install(self) -> None:
        """Exécute l'installation puis donne le focus au bouton Quitter."""
        assert self.app is not None and self.on_install is not None
        values = self.values()
        ok = await self.install.run(self.on_install, values)
        self.install_result = values if ok else None
        self.app.layout.focus(self.install.quit_btn)
        self._invalidate()

    def _move_focus(self, move: Callable[[Any], Any], event: Any) -> None:
        """Déplace le focus et valide en douceur le champ quitté.

        Args:
            move: Fonction de déplacement du focus (suivant ou précédent).
            event: Événement de touche.
        """
        self.collect()
        before = self.focused_field()
        move(event)
        if before is not None and before is not self.focused_field():
            before.validate(soft=True)

    def build_app(self, **kwargs: Any) -> Application[Any]:
        """Crée l'application prompt_toolkit (kwargs : input/output pour les tests).

        Args:
            **kwargs: Arguments passés à Application (input, output pour les tests).

        Returns:
            L'application prête à être lancée.
        """
        bindings = KeyBindings()
        idle = Condition(lambda: not self.busy)

        @bindings.add("tab", filter=idle)
        def _(event: Any) -> None:
            """Focus sur l'élément suivant.

            Args:
                event: Événement de touche.
            """
            self._move_focus(focus_next, event)

        @bindings.add("s-tab", filter=idle)
        def _(event: Any) -> None:
            """Focus sur l'élément précédent.

            Args:
                event: Événement de touche.
            """
            self._move_focus(focus_previous, event)

        @bindings.add("c-c")
        def _(event: Any) -> None:
            """Abandonne l'assistant.

            Args:
                event: Événement de touche.
            """
            event.app.exit(result=None)

        self.app = Application(
            layout=Layout(self.root, focused_element=self._first_focus()),
            key_bindings=bindings,
            style=STYLE,
            full_screen=True,
            mouse_support=idle,
            color_depth=ColorDepth.TRUE_COLOR,
            **kwargs,
        )
        return self.app

    def run(self) -> dict[str, Any] | None:
        """Lance l'assistant ; renvoie les valeurs, ou None si abandonné."""
        return self.build_app().run()

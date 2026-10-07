from __future__ import annotations

from typing import Any, Awaitable, Callable, Collection, Mapping, Sequence

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import ConditionalContainer, HSplit, Window

from .context import WizardContext
from .fields.base import Field

SubmitHandler = Callable[[WizardContext], Awaitable["str | None"]]


class Step:
    """Étape d'assistant : champs (liste ou fabrique), soumission asynchrone et visibilité."""

    def __init__(
        self,
        title: str,
        fields: Sequence[Field] | Callable[[WizardContext], Sequence[Field]],
        *,
        on_submit: SubmitHandler | None = None,
        loading_text: str = "Vérification…",
        visible_if: Callable[[WizardContext], bool] | None = None,
    ):
        """Initialise l'étape.

        Args:
            title: Titre de l'étape.
            fields: Champs, ou fabrique (contexte) renvoyant les champs.
            on_submit: Coroutine (contexte) renvoyant un message d'erreur ou None.
            loading_text: Texte affiché pendant la soumission.
            visible_if: Condition d'affichage, évaluée sur le contexte.
        """
        self.title = title
        self.on_submit = on_submit
        self.loading_text = loading_text
        self.visible_if = visible_if
        self.fields: list[Field] = []
        self.container: HSplit | None = None
        self._source = fields
        self._carry: dict[str, Any] = {}
        self._ctx = WizardContext()
        self._initial: Mapping[str, Any] = {}
        self._locked_keys: Collection[str] = ()

    @property
    def is_dynamic(self) -> bool:
        """Indique si les champs viennent d'une fabrique reconstruite à chaque entrée.

        Returns:
            True pour une fabrique.
        """
        return callable(self._source)

    def attach(
        self,
        ctx: WizardContext,
        initial: Mapping[str, Any],
        locked_keys: Collection[str],
    ) -> None:
        """Rattache l'étape au contexte et construit les champs statiques.

        Args:
            ctx: Contexte de l'assistant.
            initial: Valeurs de préremplissage par clé.
            locked_keys: Clés des champs à verrouiller.
        """
        self._ctx, self._initial, self._locked_keys = ctx, initial, locked_keys
        if not self.is_dynamic:
            self._build()

    def enter(self) -> None:
        """Prépare l'étape à l'affichage : reconstruit les champs dynamiques et rafraîchit leurs options."""
        if self.is_dynamic:
            self._build()
        for field in self.fields:
            field.on_enter()

    def _build(self) -> None:
        """Construit les champs en reportant les valeurs de la construction précédente."""
        self._carry.update({f.key: f.value for f in self.fields})
        source = self._source
        fields = list(source(self._ctx)) if callable(source) else list(source)
        for field in fields:
            field.bind(self._ctx)
            if field.key in self._locked_keys:
                field.locked = True
            for known in (self._initial, self._carry):
                if field.key in known:
                    field.set_value(known[field.key])
        self.fields = fields
        self.container = (
            HSplit([self._wrap(i, f) for i, f in enumerate(fields)]) if fields else None
        )

    def _wrap(self, index: int, field: Field) -> ConditionalContainer:
        """Enveloppe un champ avec son espacement et sa condition de visibilité.

        Args:
            index: Position du champ dans l'étape.
            field: Champ à envelopper.

        Returns:
            Le conteneur conditionnel.
        """

        def gap() -> int:
            """Hauteur de l'espace avant le champ.

            Returns:
                1 s'il y a un champ visible avant, sinon 0.
            """
            return 1 if any(f.visible for f in self.fields[:index]) else 0

        return ConditionalContainer(
            HSplit([Window(height=gap), field]),
            filter=Condition(lambda: field.visible),
        )

    def visible_fields(self) -> list[Field]:
        """Champs actuellement visibles.

        Returns:
            La liste des champs visibles.
        """
        return [f for f in self.fields if f.visible]

    def first_focus(self) -> Any:
        """Premier élément focalisable de l'étape.

        Returns:
            Le widget, ou None s'il n'y en a pas.
        """
        return next(
            (f.focus_target for f in self.fields if f.focus_target is not None), None
        )

    def first_error(self) -> Field | None:
        """Premier champ visible en erreur.

        Returns:
            Le champ, ou None.
        """
        return next((f for f in self.visible_fields() if f.error), None)

    def validate(self) -> bool:
        """Valide tous les champs visibles.

        Returns:
            True si tous sont valides.
        """
        self._ctx.refresh()
        return all([f.validate() for f in self.fields])

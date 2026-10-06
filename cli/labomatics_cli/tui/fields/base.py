from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl

from ..context import WizardContext
from ..theme import LABEL_WIDTH, LOCK_MARK
from ..widgets import is_focused

Check = Callable[[Any, Any], "str | None"]


def slugify(text: str) -> str:
    """Transforme un libellé en identifiant ASCII en minuscules.

    Args:
        text: Libellé à transformer.

    Returns:
        Le libellé sans accents, séparé par des « _ ».
    """
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


class Field:
    """Base commune des champs de formulaire : libellé, validation, visibilité et verrouillage."""

    keys_help = "Entrée valider"
    freezes_widget = True

    def __init__(
        self,
        label: str,
        *,
        key: str | None = None,
        helper: str | None = None,
        validator: Check | None = None,
        required: bool = False,
        default: Any = None,
        visible_if: Callable[[WizardContext], bool] | None = None,
        locked: bool = False,
    ):
        """Initialise le champ.

        Args:
            label: Libellé affiché devant le champ.
            key: Clé de la valeur (slug du libellé par défaut).
            helper: Texte d'aide sous le champ.
            validator: Validateur appelé avec (valeur, valeurs des autres champs).
            required: Rend le champ obligatoire.
            default: Valeur initiale.
            visible_if: Condition d'affichage, évaluée sur le contexte.
            locked: Affiche le champ en lecture seule.
        """
        self.label = label
        self.key = key or slugify(label)
        self.helper = helper
        self.validator = validator
        self.required = required
        self.default = default
        self.visible_if = visible_if
        self.locked = locked
        self.error: str | None = None
        self.ctx = WizardContext()
        self._focus: Any = None
        self._container: VSplit | None = None
        self._locked_window = Window(
            FormattedTextControl(self._locked_fragments), height=1
        )

    @property
    def value(self) -> Any:
        """Valeur courante du champ.

        Returns:
            La valeur saisie ou choisie.

        Raises:
            NotImplementedError: Doit être redéfini par les sous-classes.
        """
        raise NotImplementedError

    def set_value(self, value: Any) -> None:
        """Préremplit le champ.

        Args:
            value: Nouvelle valeur.

        Raises:
            NotImplementedError: Doit être redéfini par les sous-classes.
        """
        raise NotImplementedError

    def _widget(self) -> Any:
        """Widget prompt_toolkit propre au type de champ.

        Returns:
            Le conteneur ou la fenêtre du widget.

        Raises:
            NotImplementedError: Doit être redéfini par les sous-classes.
        """
        raise NotImplementedError

    def bind(self, ctx: WizardContext) -> None:
        """Rattache le champ au contexte de l'assistant.

        Args:
            ctx: Contexte de l'assistant.
        """
        self.ctx = ctx

    def on_enter(self) -> None:
        """Appelée à chaque affichage de l'étape (rafraîchit les options dynamiques)."""
        pass

    def _init_default(self) -> None:
        """Applique la valeur par défaut, si elle est définie."""
        if self.default is not None:
            self.set_value(self.default)

    @property
    def visible(self) -> bool:
        """Indique si le champ est affiché selon `visible_if`.

        Returns:
            True si le champ est visible.
        """
        return self.visible_if is None or bool(self.visible_if(self.ctx))

    @property
    def is_frozen(self) -> bool:
        """Indique si le champ est affiché en lecture seule.

        Returns:
            True si verrouillé et non modifiable.
        """
        return self.locked and self.freezes_widget

    @property
    def focus_target(self) -> Any:
        """Élément qui reçoit le focus pour ce champ.

        Returns:
            Le widget focalisable, ou None si caché ou verrouillé.
        """
        return None if self.is_frozen or not self.visible else self._focus

    def is_empty(self) -> bool:
        """Indique si le champ est vide.

        Returns:
            True si la valeur est vide.
        """
        return self.value in ("", None, [])

    def display_value(self) -> str:
        """Texte de la valeur pour le récapitulatif.

        Returns:
            La valeur lisible, ou « — » si vide.
        """
        return "—" if self.is_empty() else str(self.value)

    def validate(self, soft: bool = False) -> bool:
        """Valide le champ et renseigne `error`.

        Args:
            soft: Si vrai, ne signale pas un champ obligatoire vide.

        Returns:
            True si le champ est valide.
        """
        if not self.visible or self.is_frozen:
            self.error = None
        elif self.is_empty():
            self.error = "Champ obligatoire" if self.required and not soft else None
        elif self.validator:
            self.ctx.refresh()
            self.error = self.validator(self.value, self.ctx.values)
        else:
            self.error = None
        return self.error is None

    def has_focus(self) -> bool:
        """Indique si le champ porte le focus.

        Returns:
            True si le focus est dans le champ.
        """
        return self._container is not None and is_focused(self._container)

    def _box_style(self, target: Any) -> str:
        """Style de la boîte de saisie selon l'état du champ.

        Args:
            target: Widget dont on teste le focus.

        Returns:
            La classe de style prompt_toolkit.
        """
        if self.error:
            return "class:field-error"
        return "class:field-focused" if is_focused(target) else "class:field"

    def _label_fragments(self) -> list[Any]:
        """Fragments du libellé, colorés selon l'état.

        Returns:
            Les fragments de texte formaté.
        """
        if self.is_frozen:
            cls = "class:label"
        elif self.error:
            cls = "class:label-error"
        elif self.has_focus():
            cls = "class:label-focused"
        else:
            cls = "class:label"
        fragments = [(cls, self.label)]
        if self.required and not self.is_frozen:
            fragments.append(("class:required", " *"))
        return fragments

    def _locked_fragments(self) -> list[Any]:
        """Fragments de la valeur en lecture seule avec le marqueur de verrou.

        Returns:
            Les fragments de texte formaté.
        """
        return [
            ("class:locked", self.display_value()),
            ("class:locked-mark", f"  {LOCK_MARK}"),
        ]

    def _hint_visible(self) -> bool:
        """Indique si la ligne d'aide ou d'erreur est affichée.

        Returns:
            True s'il y a une erreur ou une aide.
        """
        return bool(self.error or self.helper)

    def _hint_fragments(self) -> list[Any]:
        """Fragments de la ligne d'aide ou d'erreur.

        Returns:
            Les fragments de texte formaté.
        """
        if self.error:
            return [("class:error", f"✗ {self.error}")]
        return [("class:helper", self.helper or "")]

    def _content(self) -> Any:
        """Contenu à afficher : valeur verrouillée ou widget.

        Returns:
            Le conteneur à afficher.
        """
        return self._locked_window if self.is_frozen else self._widget()

    def __pt_container__(self) -> VSplit:
        """Construit (une fois) le conteneur complet du champ.

        Returns:
            Le conteneur libellé + widget + aide.
        """
        if self._container is None:
            label = Window(
                FormattedTextControl(self._label_fragments),
                width=LABEL_WIDTH,
                height=1,
                dont_extend_width=True,
            )
            hint = ConditionalContainer(
                Window(FormattedTextControl(self._hint_fragments), height=1),
                filter=Condition(self._hint_visible),
            )
            self._container = VSplit(
                [label, HSplit([DynamicContainer(self._content), hint])]
            )
        return self._container

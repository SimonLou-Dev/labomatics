"""Design system labomatics — styles Rich personnalisés."""

from typing import Optional

from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt


import readchar
from rich.live import Live
from rich.table import Table


# Tokens du design system
COLORS = {
    "primary": "#FF6B00",  # Orange vif
    "secondary": "#1F1F1F",  # Noir/gris
    "success": "#10B981",  # Vert
    "warning": "#F59E0B",  # Amber/orange doux
    "critical": "#EF4444",  # Rouge
    "info": "#3B82F6",  # Bleu
    "cream": "#F8F4EB",  # Crème
}

# Thème Rich avec couleurs labomatics
THEME = Theme(
    {
        "info": f"bold {COLORS['info']}",
        "warning": f"bold {COLORS['warning']}",
        "error": f"bold {COLORS['critical']}",
        "success": f"bold {COLORS['success']}",
        "primary": f"bold {COLORS['primary']}",
        "secondary": f"dim {COLORS['secondary']}",
        "dim_text": "dim",
    }
)

console = Console(theme=THEME)


def title(text: str) -> None:
    """Affiche un titre principal avec la couleur primaire."""
    console.print(f"\n[{COLORS['primary']}]{'═' * 50}[/{COLORS['primary']}]")
    console.print(f"[bold {COLORS['primary']}]  {text}[/bold {COLORS['primary']}]")
    console.print(f"[{COLORS['primary']}]{'═' * 50}[/{COLORS['primary']}]\n")


def step(number: int, total: int, text: str) -> None:
    """Affiche une étape numérotée."""
    console.print(f"[bold]Step {number}/{total} — {text}[/bold]\n")


def success(text: str) -> None:
    """Message de succès."""
    console.print(f"[success]✓[/success] {text}")


def error(text: str) -> None:
    """Message d'erreur."""
    console.print(f"[error]✗[/error] {text}")


def info(text: str) -> None:
    """Message informatif."""
    console.print(f"[info]ℹ[/info] {text}")


def warning(text: str) -> None:
    """Message d'avertissement."""
    console.print(f"[warning]⚠[/warning] {text}")


def panel(text: str, title: Optional[str] = None, style: Optional[str] = None) -> None:
    """Affiche un panel avec bordure."""
    from rich.panel import Panel

    style = style or f"bold {COLORS['primary']}"
    p = Panel(text, title=title, style=style, expand=False)
    console.print(p)


def _render_table(options: list[str], cursor: int, selected: set[int]) -> Table:
    """Construit la table Rich representant l'etat courant du menu."""
    table = Table(show_header=False, box=None)
    for i, option in enumerate(options):
        case = "[x]" if i in selected else "[ ]"
        style = "bold cyan" if i == cursor else "white"
        prefix = "> " if i == cursor else "  "
        table.add_row(f"{prefix}{case} {option}", style=style)
    return table


def multi_select(choices) -> list[str]:
    """Retourne la liste des options cochees par l'utilisateur."""
    choices = list(choices)
    cursor = 0
    selected: set[int] = set()

    with Live(
        _render_table(choices, cursor, selected), console=console, auto_refresh=False
    ) as live:
        while True:
            key = readchar.readkey()

            if key == readchar.key.UP:
                cursor = (cursor - 1) % len(choices)
            elif key == readchar.key.DOWN:
                cursor = (cursor + 1) % len(choices)
            elif key == " ":
                if cursor in selected:
                    selected.remove(cursor)
                else:
                    selected.add(cursor)
            elif key == readchar.key.ENTER:
                break

            live.update(_render_table(choices, cursor, selected), refresh=True)

    return [choices[i] for i in selected]


def prompt_with_retry(
    prompt_text: str, default: Optional[str] = None, max_retries: int = 3
) -> str:
    """Prompt avec retry."""
    for _ in range(max_retries):
        value = Prompt.ask(f"  {prompt_text}", default=default)
        if value or default:
            return value or default or ""  # type: ignore
    raise RuntimeError(f"Impossible de récupérer: {prompt_text}")

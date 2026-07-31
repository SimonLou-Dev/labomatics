"""Design system labomatics — styles Rich personnalisés."""

from rich.console import Console
from rich.theme import Theme

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


def panel(text: str, title: str = None, style: str = None) -> None:
    """Affiche un panel avec bordure."""
    from rich.panel import Panel

    style = style or f"bold {COLORS['primary']}"
    p = Panel(text, title=title, style=style, expand=False)
    console.print(p)

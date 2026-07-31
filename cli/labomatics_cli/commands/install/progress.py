"""Progress tracking and display."""

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from ...utils.theme import success, error, warning

console = Console()


class ProgressTracker:
    """Suivi de la progression avec affichage."""

    def __init__(self):
        """Initialiser le tracker."""
        self.current_step = 0
        self.total_steps = 0
        self.progress = None

    def start(self, total_steps: int) -> None:
        """Démarrer le suivi."""
        self.total_steps = total_steps
        self.current_step = 0
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        self.progress.start()

    def update(self, message: str) -> None:
        """Mettre à jour le message."""
        self.current_step += 1
        if self.progress:
            self.progress.update(
                self.progress.tasks[0].id,
                description=f"[{self.current_step}/{self.total_steps}] {message}",
            )

    def stop(self) -> None:
        """Arrêter le suivi."""
        if self.progress:
            self.progress.stop()

    def section(self, title: str) -> None:
        """Afficher un titre de section."""
        if self.progress:
            self.progress.stop()
        console.print(f"\n[bold cyan]═══ {title} ═══[/bold cyan]")
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        self.progress.start()

    def error(self, message: str) -> None:
        """Afficher une erreur."""
        if self.progress:
            self.progress.stop()
        error(message)

    def success_msg(self, message: str) -> None:
        """Afficher un succès."""
        if self.progress:
            self.progress.stop()
        success(message)
        if self.total_steps > 0:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            )
            self.progress.start()

    def warning_msg(self, message: str) -> None:
        """Afficher un avertissement."""
        if self.progress:
            self.progress.stop()
        warning(message)
        if self.total_steps > 0:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            )
            self.progress.start()

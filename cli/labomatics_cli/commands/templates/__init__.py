"""Installation command - main entry point."""

from rich.prompt import Confirm

from ...utils.theme import console
from ...utils.state import InstallState

from .orchestrator import run_installation


def cmd_templates(args) -> int:
    """Installer les templates sur un cluster."""
    state = InstallState()

    # Check for in-progress installation
    if state.is_in_progress():
        domain = state.get("domain")
        console.print(f"\n[yellow]Vous êtres sur le cluster de {domain} ")

        if Confirm.ask("Confirmez vous?", default=True):
            console.print("[dim]Démarage du gestionaire de tempaltes...[/dim]\n")
        else:
            console.print("[yellow]Opération annulée[/yellow]")
            return 1

    try:
        return run_installation(state)
    except KeyboardInterrupt:
        console.print("\n[yellow]Opération annulée[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Erreur:[/red] {e}")
        import traceback

        traceback.print_exc()
        return 1

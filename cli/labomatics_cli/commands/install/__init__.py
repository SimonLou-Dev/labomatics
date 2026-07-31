"""Installation command - main entry point."""

from rich.prompt import Confirm

from ...utils.theme import console
from ...utils.state import InstallState

from .orchestrator import run_installation


def cmd_install(args) -> int:
    """Installer le cluster central sur Proxmox."""
    state = InstallState()

    # Check for in-progress installation
    if state.is_in_progress():
        domain = state.get("domain")
        last_step = state.get_last_completed_step()
        console.print(
            f"\n[yellow]⚠ Installation en cours pour {domain} "
            f"(dernière étape: {last_step})[/yellow]"
        )

        if Confirm.ask("Continuer cette installation?", default=True):
            console.print("[dim]Reprise de l'installation...[/dim]\n")
        else:
            if Confirm.ask("Recommencer à zéro?", default=False):
                state.clear()
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

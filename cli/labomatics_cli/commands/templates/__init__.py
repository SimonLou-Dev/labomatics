"""Installation command - main entry point."""

from ...utils.proxmox import ProxmoxClient
from ...utils.theme import console
from .build_openwrt import _resolve_node, _resolve_proxmox_connection
from .orchestrator import run_installation


def cmd_templates(args) -> int:
    """Construit les templates VM (alpine/debian/el/ubuntu…) sur un cluster.

    Args:
        args: Arguments de la ligne de commande (`cluster`, `cluster_url`, `user`,
            `token_id`, `token_secret`, `node`, `ssh_host`).

    Returns:
        0 en cas de succès, 1 en cas d'abandon ou d'erreur.
    """
    try:
        url, user, token_id, token_secret = _resolve_proxmox_connection(args)
        pve = ProxmoxClient(url, user, token_id, token_secret)
        node, ssh_host = _resolve_node(pve, args)
        return run_installation(pve, node, ssh_host)
    except KeyboardInterrupt:
        console.print("\n[yellow]Opération annulée[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Erreur:[/red] {e}")
        import traceback

        traceback.print_exc()
        return 1

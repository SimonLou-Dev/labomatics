#!/usr/bin/env python3
"""
Commande ``destroy-all`` — supprime toutes les ressources étudiants.

Détruit VMs, VNets, ACL, utilisateurs et pools de tous les étudiants gérés.
Équivaut à un ``apply`` avec un CSV vide.
"""

from rich.console import Console

from ..config import load_config
from ..proxmox import list_managed_pools
from ._helpers import ask_confirm, make_connection
from .apply import apply_removes

console = Console()


def cmd_destroy_all(args) -> None:
    """Supprime toutes les ressources Proxmox de tous les étudiants gérés."""
    config = load_config()
    proxmox = make_connection()

    pools = list_managed_pools(proxmox)
    if not pools:
        console.print("[dim]Aucun pool géré trouvé — rien à supprimer.[/dim]")
        return

    console.print(f"\n[bold red]⚠  {len(pools)} pool(s) seront supprimés :[/bold red]")
    for p in pools:
        console.print(f"  • {p['poolid']}")

    if not getattr(args, "yes", False):
        if not ask_confirm("Supprimer TOUTES les ressources étudiants ? (irréversible)"):
            console.print("[dim]Annulé.[/dim]")
            return

    apply_removes(proxmox, config, pools)
    console.print("\n[bold red]✓ Toutes les ressources étudiants supprimées.[/bold red]\n")

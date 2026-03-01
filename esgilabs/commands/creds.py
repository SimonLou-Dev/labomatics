#!/usr/bin/env python3
"""
Commande ``credentials`` — affichage des credentials étudiants.

Lit ``credentials.csv`` (généré par ``apply``) et l'affiche sous forme de
tableau Rich. Ne fait aucun appel API Proxmox.

.. warning::
    Les mots de passe sont affichés en clair. Réserver l'accès à cette
    commande aux administrateurs.
"""

from rich.console import Console
from rich.table import Table

from ..config import load_config
from ..credentials import creds_path, load_credentials

console = Console()


def cmd_credentials(_) -> None:
    """Affiche les credentials étudiants depuis ``credentials.csv``."""
    cfg = load_config()
    path = creds_path(cfg)

    if not path.exists():
        console.print("[dim]Aucun fichier credentials.csv. Lancez 'apply' d'abord.[/dim]")
        return

    creds = load_credentials(cfg)
    if not creds:
        console.print("[dim]Aucun credential stocké.[/dim]")
        return

    table = Table(
        show_header=True, header_style="bold magenta",
        title="Credentials étudiants",
    )
    table.add_column("Nom", style="cyan")
    table.add_column("User Proxmox")
    table.add_column("Password")
    table.add_column("WAN IP")

    for row in sorted(creds.values(), key=lambda r: r["nom"]):
        table.add_row(row["nom"], row["userid"], row["password"], row["wan_ip"])

    console.print(table)
    console.print(f"\n  {len(creds)} étudiant(s) — {path}\n")

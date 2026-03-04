#!/usr/bin/env python3
"""
Commande ``init`` — initialisation de la configuration labomatics.

Crée /etc/labomatics/ avec les fichiers de configuration par défaut
(infra.yaml, .env, students.csv) si non présents.
"""

import shutil
from pathlib import Path

from rich.console import Console

console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
CONFIG_DIR = Path("/etc/labomatics")


def cmd_init(args) -> None:
    """Initialise la configuration labomatics dans /etc/labomatics/."""
    target_dir = getattr(args, "dir", None)
    config_dir = Path(target_dir) if target_dir else CONFIG_DIR

    console.print(f"\n[bold cyan]Initialisation de labomatics → {config_dir}[/bold cyan]\n")

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        console.print(
            f"[red]❌ Permission refusée pour créer {config_dir}[/red]\n"
            f"Essayez : [bold]sudo labomatics init[/bold]\n"
            f"Ou spécifiez un répertoire : [bold]labomatics init --dir ./config[/bold]"
        )
        return

    files = [
        ("infra.yaml.example", "infra.yaml"),
        (".env.example", ".env"),
        ("students.csv.example", "students.csv"),
    ]

    for src_name, dst_name in files:
        src = TEMPLATES_DIR / src_name
        dst = config_dir / dst_name

        if dst.exists():
            console.print(f"  [dim]⏭  {dst_name} — déjà présent, ignoré[/dim]")
            continue

        if src.exists():
            shutil.copy(src, dst)
            console.print(f"  [green]✓ {dst_name} créé[/green]")
        else:
            console.print(f"  [yellow]⚠  Template {src_name} introuvable (package incomplet)[/yellow]")

    console.print(f"""
[bold]Étapes suivantes :[/bold]

  1. Éditer [cyan]{config_dir}/.env[/cyan] avec vos credentials Proxmox :
       PROXMOX_HOST=192.168.1.100
       PROXMOX_TOKEN_ID=root@pam!labomatics
       PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

  2. Éditer [cyan]{config_dir}/infra.yaml[/cyan] selon votre infrastructure

  3. Remplir [cyan]{config_dir}/students.csv[/cyan] avec vos étudiants

  4. Tester la connexion : [bold]labomatics pools[/bold]

  5. Vérifier les changements : [bold]labomatics diff[/bold]

  6. Appliquer : [bold]labomatics apply[/bold]
""")

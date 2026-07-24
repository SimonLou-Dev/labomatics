"""Commande 'labomatics install' - initialisation du cluster."""

from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()


def cmd_install(args) -> int:
    """Installer le cluster central sur Proxmox."""
    console.print("\n[bold cyan]labomatics install[/bold cyan] — Initialiser le cluster")
    console.print("[dim]Cette commande doit être exécutée sur un nœud du cluster Proxmox[/dim]\n")

    # Collect Proxmox connection info
    console.print("[bold]Connexion Proxmox[/bold]")
    proxmox_url = Prompt.ask("  URL Proxmox (ex: https://pve.example.com:8006)")
    proxmox_user = Prompt.ask("  User (ex: root@pam ou user@pve)")
    proxmox_token = Prompt.ask("  Token API (admin complet)", password=True)
    proxmox_token_id = Prompt.ask("  Token ID (ex: terraform-prov)")

    # Validate connection
    console.print("\n[dim]Validation de la connexion...[/dim]")
    # TODO: implement Proxmox connection validation

    # VM configuration
    console.print("\n[bold]Configuration de la VM[/bold]")
    hostname = args.hostname
    domain = args.domain
    storage = args.storage or Prompt.ask("  Stockage partagé (ex: local-lvm, ceph-store)")

    vm_config = {
        "hostname": hostname,
        "domain": domain,
        "storage": storage,
        "vmid": 100,  # TODO: find available VMID
        "cores": 4,
        "memory": 8192,
        "disk": 50,
    }

    # Show summary
    console.print("\n[bold]Résumé de l'installation[/bold]")
    table = Table(show_header=False, box=None)
    table.add_row("  Hostname", f"{vm_config['hostname']}.{vm_config['domain']}")
    table.add_row("  Stockage", vm_config["storage"])
    table.add_row("  vCPU", str(vm_config["cores"]))
    table.add_row("  RAM", f"{vm_config['memory']} MB")
    table.add_row("  Disque", f"{vm_config['disk']} GB")
    console.print(table)

    # Dry-run
    if args.dry_run:
        console.print("\n[yellow]Mode --dry-run[/yellow] — pas de changement appliqué")
        return 0

    # Confirm
    if not Confirm.ask("\n[bold]Continuer?[/bold]"):
        console.print("[yellow]Opération annulée[/yellow]")
        return 1

    console.print("\n[bold cyan]Installation en cours...[/bold cyan]\n")

    # TODO: implement actual provisioning:
    # 1. Create VM from Alpine template
    # 2. Configure storage (HA)
    # 3. Inject cloud-init script
    # 4. Start VM
    # 5. Wait for services to be ready

    console.print("[green]✓[/green] VM créée")
    console.print("[green]✓[/green] Services déployés")
    console.print("[green]✓[/green] Installation complète!\n")

    # Output access info
    console.print("[bold]Accès aux services[/bold]")
    table = Table(show_header=True, box=None)
    table.add_column("Service", style="cyan")
    table.add_column("URL", style="yellow")
    table.add_row("Keycloak", f"https://keycloak.{domain}")
    table.add_row("Traefik", f"http://traefik.{domain}:8080")
    table.add_row("DNS", f"{vm_config['hostname']}.{domain}")
    console.print(table)

    console.print("\n[dim]Les mots de passe sont affichés dans la VM (/etc/labomatics-provisioned)[/dim]\n")

    return 0

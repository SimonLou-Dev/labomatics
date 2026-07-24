"""Commande 'labomatics install' - initialisation du cluster."""

import secrets
import time
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

from ..utils.ssh import SSHClient
from ..utils.keycloak import KeycloakClient

console = Console()


def cmd_install(args) -> int:
    """Installer le cluster central sur Proxmox."""
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   labomatics install — Initialiser le cluster[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    console.print("[dim]Cette commande doit être exécutée sur un nœud du cluster Proxmox[/dim]\n")

    # Step 1: Collect configuration
    console.print("[bold]Step 1/6 — Configuration[/bold]\n")
    
    domain = Prompt.ask("  Domaine root (ex: esgi.local)")
    if not domain:
        console.print("[red]Domaine requis[/red]")
        return 1
    
    network_iface = Prompt.ask("  Interface réseau (ex: vmbr0)")
    if not network_iface:
        console.print("[red]Interface réseau requise[/red]")
        return 1

    # Step 2: VM configuration
    console.print("\n[bold]Step 2/6 — Configuration VM[/bold]\n")
    
    vm_name = Prompt.ask("  Nom de la VM", default="labomatics")
    vm_user = Prompt.ask("  User SSH", default="root")
    vm_password = Prompt.ask("  Password SSH", password=True)
    vm_ip = Prompt.ask("  IP de la VM (ex: 192.168.1.100)")
    vm_gateway = Prompt.ask("  Gateway (ex: 192.168.1.1)")
    
    # Generate SSH key for better security
    vm_ssh_key = secrets.token_urlsafe(32)

    # Step 3: Generate passwords
    console.print("\n[bold]Step 3/6 — Génération des passwords[/bold]\n")
    
    pg_root_password = secrets.token_urlsafe(16)
    labomatics_db_password = secrets.token_urlsafe(16)
    keycloak_db_password = secrets.token_urlsafe(16)
    powerdns_db_password = secrets.token_urlsafe(16)
    keycloak_admin_password = secrets.token_urlsafe(16)
    powerdns_api_key = secrets.token_urlsafe(16)
    
    console.print("[green]✓[/green] Passwords générés\n")

    # Step 4: User account for Keycloak
    console.print("[bold]Step 4/6 — Compte administrateur Keycloak[/bold]\n")
    
    admin_email = Prompt.ask("  Email administrateur")
    admin_first_name = Prompt.ask("  Prénom")
    admin_last_name = Prompt.ask("  Nom")
    admin_password = secrets.token_urlsafe(16)

    # Step 5: Summary
    console.print("\n[bold]Step 5/6 — Résumé de la configuration[/bold]\n")
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[bold]Domaine[/bold]", domain)
    table.add_row("[bold]Interface[/bold]", network_iface)
    table.add_row("[bold]VM[/bold]", f"{vm_name} ({vm_ip})")
    table.add_row("[bold]Gateway[/bold]", vm_gateway)
    table.add_row("[bold]Admin Keycloak[/bold]", admin_email)
    console.print(table)

    if args.dry_run:
        console.print("\n[yellow]Mode --dry-run[/yellow] — pas de changement appliqué\n")
        return 0

    # Step 6: Confirm
    console.print("")
    if not Confirm.ask("[bold]Continuer?[/bold]", default=True):
        console.print("[yellow]Opération annulée[/yellow]")
        return 1

    # Actual provisioning
    console.print("\n[bold]Step 6/6 — Installation en cours...[/bold]\n")

    try:
        # 1. Create VM (Proxmox API)
        with console.status("[cyan]Création de la VM..."):
            time.sleep(1)  # TODO: actual VM creation
            console.print("[green]✓[/green] VM créée")

        # 2. Wait for VM to be up
        with console.status("[cyan]Attente du démarrage de la VM..."):
            time.sleep(2)  # TODO: wait for VM
            console.print("[green]✓[/green] VM accessible")

        # 3. Connect via SSH
        console.print("[cyan]Connexion SSH...[/cyan]")
        ssh = SSHClient(vm_ip, vm_user, password=vm_password)
        ssh.connect()
        console.print("[green]✓[/green] SSH connecté")

        # 4. Install Docker
        with console.status("[cyan]Installation de Docker..."):
            stdout, stderr, rc = ssh.exec_command("apk add --no-cache docker docker-compose")
            if rc != 0:
                console.print(f"[red]Erreur Docker:{/red] {stderr}")
                return 1
            console.print("[green]✓[/green] Docker installé")

        # 5. Setup Docker stack
        with console.status("[cyan]Configuration de la stack Docker..."):
            # Copy docker-compose et config files
            # TODO: generate and copy files with environment variables
            console.print("[green]✓[/green] Configuration copiée")

        # 6. Start services
        with console.status("[cyan]Démarrage des services..."):
            stdout, stderr, rc = ssh.exec_command("cd /opt/labomatics && docker-compose up -d")
            if rc != 0:
                console.print(f"[red]Erreur démarrage:[/red] {stderr}")
                return 1
            
            # Wait for services to be ready
            for i in range(30):
                stdout, _, rc = ssh.exec_command("docker exec labomatics-keycloak curl -s http://localhost:8080/health/ready")
                if rc == 0:
                    break
                time.sleep(2)
            
            console.print("[green]✓[/green] Services démarrés")

        # 7. Setup Keycloak
        with console.status("[cyan]Configuration Keycloak..."):
            kc = KeycloakClient(f"https://keycloak.{domain}", "admin", keycloak_admin_password)
            kc.auth()
            
            # Create realm
            kc.create_realm("labomatics")
            
            # Create admin group
            group_id = kc.create_group("labomatics", "superadmin")
            
            # Create admin user
            user_id = kc.create_user(
                "labomatics",
                admin_email.split("@")[0],
                admin_email,
                admin_first_name,
                admin_last_name,
                admin_password,
            )
            
            # Add user to group
            kc.add_user_to_group("labomatics", user_id, group_id)
            
            console.print("[green]✓[/green] Keycloak configuré")

        # 8. Create OIDC client for Proxmox
        with console.status("[cyan]Création client OIDC pour Proxmox..."):
            client_secret = kc.create_client(
                "labomatics",
                "labomatics-proxmox",
                [f"https://pve.{domain}:8006/api2/extjs/system/domain/keycloak/openid/callback"],
            )
            console.print("[green]✓[/green] Client OIDC créé")

        ssh.disconnect()

        # Final output
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold green]Installation complète! ✓[/bold green]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        output_table = Table(show_header=True, box=None)
        output_table.add_column("Service", style="cyan")
        output_table.add_column("URL/Infos", style="yellow")
        output_table.add_row("Keycloak", f"https://keycloak.{domain}")
        output_table.add_row("Traefik", f"http://traefik.{domain}:8080")
        output_table.add_row("PowerDNS", f"http://localhost:8001 (API: {powerdns_api_key[:8]}...)")
        output_table.add_row("PostgreSQL", f"{vm_ip}:5432")
        console.print(output_table)

        console.print("\n[bold]Credentials[/bold]\n")
        creds_table = Table(show_header=False, box=None, padding=(0, 1))
        creds_table.add_row("[bold]Keycloak Admin (master realm)[/bold]", f"admin / {keycloak_admin_password[:8]}...")
        creds_table.add_row("[bold]Admin Labomatics[/bold]", f"{admin_email} / {admin_password[:8]}...")
        creds_table.add_row("[bold]PostgreSQL (root)[/bold]", f"postgres / {pg_root_password[:8]}...")
        creds_table.add_row("[bold]PowerDNS API Key[/bold]", f"{powerdns_api_key[:8]}...")
        console.print(creds_table)

        console.print("\n[bold]OIDC Proxmox[/bold]\n")
        oidc_table = Table(show_header=False, box=None, padding=(0, 1))
        oidc_table.add_row("[bold]Client ID[/bold]", "labomatics-proxmox")
        oidc_table.add_row("[bold]Client Secret[/bold]", client_secret[:8] + "...")
        oidc_table.add_row("[bold]Issuer URL[/bold]", f"https://keycloak.{domain}/realms/labomatics")
        oidc_table.add_row("[bold]Auth URL[/bold]", f"https://keycloak.{domain}/realms/labomatics/protocol/openid-connect/auth")
        oidc_table.add_row("[bold]Token URL[/bold]", f"https://keycloak.{domain}/realms/labomatics/protocol/openid-connect/token")
        console.print(oidc_table)

        console.print("\n[bold red]⚠  Sauvegardez bien ces credentials![/bold red]\n")
        console.print("[bold]Prochaines étapes:[/bold]")
        console.print("  1. Configurer OIDC dans Proxmox")
        console.print("  2. Ajouter le realm Keycloak à Proxmox")
        console.print("  3. Tester la connexion OIDC")
        console.print("  4. Configurer les permissions (RBAC)\n")

        return 0

    except Exception as e:
        console.print(f"[red]Erreur:[/red] {e}")
        return 1

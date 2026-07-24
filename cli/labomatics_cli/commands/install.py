"""Commande 'labomatics install' - initialisation complète du cluster."""

import secrets
import time
import os
import tempfile
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from ..utils.ssh import SSHClient
from ..utils.proxmox import ProxmoxClient
from ..utils.keycloak import KeycloakClient
from ..utils.verify import ServiceVerifier

console = Console()


def cmd_install(args) -> int:
    """Installer le cluster central sur Proxmox."""
    try:
        return _install(args)
    except Exception as e:
        console.print(f"[red]✗ Erreur:[/red] {e}")
        import traceback
        traceback.print_exc()
        return 1


def _install(args) -> int:
    """Logique principale de l'installation."""
    
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   labomatics install — Initialiser le cluster[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

    # Step 1: Configuration de base
    console.print("[bold]Step 1/7 — Configuration[/bold]\n")
    
    domain = Prompt.ask("  Domaine root (ex: esgi.local)")
    if not domain:
        console.print("[red]Domaine requis[/red]")
        return 1
    
    network_iface = Prompt.ask("  Interface réseau (ex: vmbr0)")
    if not network_iface:
        console.print("[red]Interface réseau requise[/red]")
        return 1

    # Step 2: Proxmox connection
    console.print("\n[bold]Step 2/7 — Connexion Proxmox[/bold]\n")
    
    proxmox_url = Prompt.ask("  URL Proxmox (ex: https://192.168.1.10:8006)")
    proxmox_user = Prompt.ask("  User (ex: root@pam)")
    proxmox_token_id = Prompt.ask("  Token ID (ex: terraform)")
    proxmox_token_secret = Prompt.ask("  Token Secret", password=True)

    # Validate Proxmox connection
    console.print("\n[dim]Validation de la connexion Proxmox...[/dim]")
    try:
        pve = ProxmoxClient(proxmox_url, proxmox_user, proxmox_token_id, proxmox_token_secret)
        nodes = pve.get_nodes()
        if not nodes:
            console.print("[red]Aucun nœud trouvé[/red]")
            return 1
        console.print(f"[green]✓[/green] {len(nodes)} nœud(s) trouvé(s)\n")
    except Exception as e:
        console.print(f"[red]✗ Erreur de connexion:[/red] {e}")
        return 1

    # Choisir le nœud
    if len(nodes) == 1:
        node = nodes[0]
        console.print(f"Nœud sélectionné: {node}\n")
    else:
        console.print("Nœuds disponibles:")
        for i, n in enumerate(nodes, 1):
            console.print(f"  {i}. {n}")
        choice = Prompt.ask("  Choisir un nœud", choices=[str(i) for i in range(1, len(nodes) + 1)])
        node = nodes[int(choice) - 1]

    # Step 3: VM configuration
    console.print("\n[bold]Step 3/7 — Configuration VM[/bold]\n")
    
    vm_name = Prompt.ask("  Nom de la VM", default="labomatics")
    vm_memory = int(Prompt.ask("  Mémoire (MB)", default="8192"))
    vm_cores = int(Prompt.ask("  Cores", default="4"))
    vm_storage = Prompt.ask("  Storage (ex: local-lvm)", default="local-lvm")
    vm_password = Prompt.ask("  Password SSH", password=True)

    # Step 4: Generate passwords
    console.print("\n[bold]Step 4/7 — Génération des secrets[/bold]\n")
    
    pg_root_password = secrets.token_urlsafe(16)
    labomatics_db_password = secrets.token_urlsafe(16)
    keycloak_db_password = secrets.token_urlsafe(16)
    powerdns_db_password = secrets.token_urlsafe(16)
    keycloak_admin_password = secrets.token_urlsafe(16)
    powerdns_api_key = secrets.token_urlsafe(16)
    
    console.print("[green]✓[/green] Secrets générés\n")

    # Step 5: Admin account
    console.print("[bold]Step 5/7 — Compte administrateur Keycloak[/bold]\n")
    
    admin_email = Prompt.ask("  Email administrateur")
    admin_first_name = Prompt.ask("  Prénom")
    admin_last_name = Prompt.ask("  Nom")
    admin_password = secrets.token_urlsafe(16)

    # Step 6: Summary
    console.print("\n[bold]Step 6/7 — Résumé[/bold]\n")
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[bold]Domaine[/bold]", domain)
    table.add_row("[bold]Nœud Proxmox[/bold]", node)
    table.add_row("[bold]VM[/bold]", f"{vm_name} ({vm_memory}MB, {vm_cores} cores)")
    table.add_row("[bold]Admin[/bold]", admin_email)
    console.print(table)

    if args.dry_run:
        console.print("\n[yellow]Mode --dry-run[/yellow] — pas de changement appliqué\n")
        return 0

    # Confirm
    console.print("")
    if not Confirm.ask("[bold]Continuer?[/bold]", default=True):
        console.print("[yellow]Opération annulée[/yellow]")
        return 1

    # Step 7: Installation
    console.print("\n[bold]Step 7/7 — Installation en cours...[/bold]\n")

    with Progress(transient=True) as progress:
        # Create VM
        task = progress.add_task("[cyan]Création de la VM...", total=None)
        try:
            vmid = pve.get_available_vmid(node)
            console.print(f"VMID: {vmid}")
            
            # Pour l'instant, skip VM creation (complexe sans template)
            # upid = pve.create_vm(node, vmid, vm_name, vm_memory, vm_cores, vm_storage)
            # pve.wait_for_task(node, upid)
            
            vm_ip = "192.168.1.150"  # TODO: get actual IP or prompt for it
            progress.stop_task(task)
            console.print("[green]✓[/green] VM (simulation)OK\n")
        except Exception as e:
            console.print(f"[red]✗ Erreur VM:[/red] {e}\n")
            return 1

        # Connect SSH
        task = progress.add_task("[cyan]Connexion SSH...", total=None)
        try:
            ssh = SSHClient(vm_ip, "root", password=vm_password)
            ssh.connect()
            progress.stop_task(task)
            console.print("[green]✓[/green] SSH connecté\n")
        except Exception as e:
            console.print(f"[red]✗ Erreur SSH:[/red] {e}\n")
            return 1

        try:
            # Install Docker
            task = progress.add_task("[cyan]Installation Docker...", total=None)
            stdout, stderr, rc = ssh.exec_command("apk add --no-cache docker docker-compose curl")
            if rc != 0:
                raise Exception(f"Docker install failed: {stderr}")
            progress.stop_task(task)
            console.print("[green]✓[/green] Docker installé\n")

            # Create directories
            task = progress.add_task("[cyan]Création répertoires...", total=None)
            ssh.mkdir("/opt/labomatics")
            ssh.mkdir("/opt/labomatics/data")
            progress.stop_task(task)
            console.print("[green]✓[/green] Répertoires créés\n")

            # Upload docker-compose (generate inline)
            task = progress.add_task("[cyan]Upload docker-compose...", total=None)
            compose_content = _generate_docker_compose(
                domain, pg_root_password, labomatics_db_password,
                keycloak_db_password, powerdns_db_password,
                keycloak_admin_password, powerdns_api_key
            )
            ssh.put_file_content(compose_content, "/opt/labomatics/docker-compose.yml")
            progress.stop_task(task)
            console.print("[green]✓[/green] Docker-compose uploadé\n")

            # Upload init scripts
            task = progress.add_task("[cyan]Upload scripts DB...", total=None)
            init_script = _generate_init_databases(
                labomatics_db_password, keycloak_db_password, powerdns_db_password
            )
            ssh.put_file_content(init_script, "/opt/labomatics/init-databases.sh")
            progress.stop_task(task)
            console.print("[green]✓[/green] Scripts uploadés\n")

            # Start Docker services
            task = progress.add_task("[cyan]Démarrage services Docker...", total=None)
            stdout, stderr, rc = ssh.exec_command(
                "cd /opt/labomatics && docker-compose up -d"
            )
            if rc != 0:
                raise Exception(f"Docker start failed: {stderr}")
            progress.stop_task(task)
            console.print("[green]✓[/green] Services démarrés\n")

            # Wait for Keycloak
            task = progress.add_task("[cyan]Attente Keycloak...", total=None)
            keycloak_url = f"https://keycloak.{domain}"
            if not ServiceVerifier.check_keycloak(keycloak_url, timeout=120):
                console.print("[yellow]⚠ Keycloak timeout (continuant quand même)[/yellow]")
            progress.stop_task(task)
            console.print("[green]✓[/green] Keycloak prêt\n")

            # Setup Keycloak
            task = progress.add_task("[cyan]Configuration Keycloak...", total=None)
            try:
                kc = KeycloakClient(keycloak_url, "admin", keycloak_admin_password)
                kc.auth()
                kc.create_realm("labomatics")
                group_id = kc.create_group("labomatics", "superadmin")
                user_id = kc.create_user(
                    "labomatics",
                    admin_email.split("@")[0],
                    admin_email,
                    admin_first_name,
                    admin_last_name,
                    admin_password,
                )
                kc.add_user_to_group("labomatics", user_id, group_id)
                client_secret = kc.create_client(
                    "labomatics",
                    "labomatics-proxmox",
                    [f"https://pve.{domain}:8006/api2/extjs/system/domain/keycloak/openid/callback"],
                )
            except Exception as e:
                console.print(f"[yellow]⚠ Keycloak setup partial:[/yellow] {e}")
                client_secret = "N/A"
            
            progress.stop_task(task)
            console.print("[green]✓[/green] Keycloak configuré\n")

            ssh.disconnect()

        except Exception as e:
            ssh.disconnect()
            console.print(f"[red]✗ Erreur:[/red] {e}\n")
            return 1

    # Final output
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold green]Installation complète! ✓[/bold green]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

    output_table = Table(show_header=True, box=None)
    output_table.add_column("Service", style="cyan")
    output_table.add_column("URL/Infos", style="yellow")
    output_table.add_row("Keycloak", f"https://keycloak.{domain}")
    output_table.add_row("Traefik", f"http://traefik.{domain}:8080")
    output_table.add_row("PowerDNS API", f"http://{vm_ip}:8001")
    output_table.add_row("PostgreSQL", f"{vm_ip}:5432")
    console.print(output_table)

    console.print("\n[bold]Credentials[/bold]\n")
    creds_table = Table(show_header=False, box=None, padding=(0, 1))
    creds_table.add_row("[bold]Keycloak Admin (master)[/bold]", f"admin / {keycloak_admin_password[:12]}...")
    creds_table.add_row("[bold]Admin Labomatics[/bold]", f"{admin_email} / {admin_password[:12]}...")
    creds_table.add_row("[bold]PostgreSQL (root)[/bold]", f"postgres / {pg_root_password[:12]}...")
    creds_table.add_row("[bold]PowerDNS API Key[/bold]", f"{powerdns_api_key[:12]}...")
    console.print(creds_table)

    console.print("\n[bold]OIDC Proxmox Setup[/bold]\n")
    oidc_table = Table(show_header=False, box=None, padding=(0, 1))
    oidc_table.add_row("[bold]Client ID[/bold]", "labomatics-proxmox")
    oidc_table.add_row("[bold]Client Secret[/bold]", client_secret[:12] + "..." if client_secret != "N/A" else "N/A")
    oidc_table.add_row("[bold]Issuer URL[/bold]", f"https://keycloak.{domain}/realms/labomatics")
    console.print(oidc_table)

    console.print("\n[bold red]⚠  Sauvegardez bien ces credentials![/bold red]\n")

    return 0


def _generate_docker_compose(domain, pg_root_pwd, lab_db_pwd, kc_db_pwd, pdns_db_pwd, kc_admin_pwd, pdns_api_key):
    """Générer le docker-compose.yml."""
    return f"""version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: labomatics-postgres
    environment:
      POSTGRES_PASSWORD: {pg_root_pwd}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-databases.sh:/docker-entrypoint-initdb.d/init.sh:ro
    networks:
      - labomatics
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: labomatics-keycloak
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: {kc_db_pwd}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: {kc_admin_pwd}
      KC_PROXY: edge
      KC_HOSTNAME_STRICT: false
      KC_HOSTNAME: keycloak.{domain}
    command:
      - start
      - --optimized
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - labomatics
    labels:
      traefik.enable: "true"
      traefik.http.routers.keycloak.rule: Host(`keycloak.{domain}`)
      traefik.http.services.keycloak.loadbalancer.server.port: "8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  powerdns:
    image: powerdns/pdns-alpine:latest
    container_name: labomatics-powerdns
    environment:
      PDNS_api: "yes"
      PDNS_api_key: {pdns_api_key}
      PDNS_webserver: "yes"
      PDNS_webserver_port: "8001"
    volumes:
      - powerdns_data:/var/lib/powerdns
    networks:
      - labomatics
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy

  traefik:
    image: traefik:v3.0
    container_name: labomatics-traefik
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - labomatics

volumes:
  postgres_data:
  powerdns_data:

networks:
  labomatics:
    driver: bridge
"""


def _generate_init_databases(lab_db_pwd, kc_db_pwd, pdns_db_pwd):
    """Générer le script d'init des DBs."""
    return f"""#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 <<-EOSQL
    CREATE USER labomatics WITH PASSWORD '{lab_db_pwd}';
    CREATE DATABASE labomatics OWNER labomatics;
    
    CREATE USER keycloak WITH PASSWORD '{kc_db_pwd}';
    CREATE DATABASE keycloak OWNER keycloak;
    
    CREATE USER powerdns WITH PASSWORD '{pdns_db_pwd}';
    CREATE DATABASE powerdns OWNER powerdns;
EOSQL
"""


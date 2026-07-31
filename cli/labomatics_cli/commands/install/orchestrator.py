"""Installation orchestrator - main workflow."""

from rich.prompt import Confirm
from rich.table import Table

from ...utils.theme import console, title, success
from ...utils.proxmox import ProxmoxClient
from ...utils.state import InstallState

from .steps import (
    collect_step_1_basic_config,
    collect_step_2_proxmox_connection,
    collect_step_3_network_config,
    collect_step_4_proxmox_user,
    collect_step_5_vm_config,
    collect_step_6_download_image,
    collect_step_7_secrets,
    collect_step_8_admin_account,
)
from .vm import VMDeployer
from .network import NetworkSetup
from .keycloak import KeycloakSetup
from .proxmox_oidc import ProxmoxOIDCSetup


def run_installation(state: InstallState) -> int:
    """Orchestrer l'installation."""
    title("labomatics install — Initialiser le cluster")

    if not state.is_in_progress():
        state.mark_in_progress("initializing...")

    # Collect all configuration
    domain, network_iface, wan_iface = collect_step_1_basic_config(state)
    (
        proxmox_url,
        proxmox_user,
        proxmox_token_id,
        proxmox_token_secret,
        node,
    ) = collect_step_2_proxmox_connection(state)

    pve = ProxmoxClient(
        proxmox_url, proxmox_user, proxmox_token_id, proxmox_token_secret
    )

    wan_config, vxlan_config, dns_servers = collect_step_3_network_config(state)
    labomatics_user, labomatics_token_secret = collect_step_4_proxmox_user(
        state, pve, domain
    )
    (
        vm_name,
        vm_memory,
        vm_cores,
        vm_storage,
        vm_password,
        ssh_pubkeys,
        ssh_privkey_path,
    ) = collect_step_5_vm_config(state)
    image_filename = collect_step_6_download_image(state, pve, node, vm_storage)
    (
        pg_root_password,
        labomatics_db_password,
        keycloak_db_password,
        keycloak_admin_password,
    ) = collect_step_7_secrets(state)
    admin_email, admin_first_name, admin_last_name = collect_step_8_admin_account(state)

    # Display summary and confirm
    _display_summary(
        domain,
        node,
        vm_name,
        vm_memory,
        vm_cores,
        wan_config,
        vxlan_config,
        admin_email,
    )
    if not Confirm.ask("[bold]Continuer?[/bold]", default=True):
        return 1

    # Deploy VM and infrastructure
    vm_deployer = VMDeployer(pve, node, state)
    vm_ip = vm_deployer.deploy(
        vm_name,
        vm_memory,
        vm_cores,
        vm_storage,
        image_filename,
        wan_config,
        vm_password,
        ssh_pubkeys,
    )

    # Setup on VM
    network_setup = NetworkSetup(pve, domain, vm_ip, ssh_privkey_path, state)
    network_setup.setup_all(wan_config, vxlan_config, dns_servers, node)

    # Configure services
    kc_setup = KeycloakSetup(domain, keycloak_admin_password, state, pve)
    kc_setup.setup(admin_first_name, admin_last_name, admin_email)

    oidc_setup = ProxmoxOIDCSetup(pve, domain, state)
    oidc_setup.setup(admin_first_name, admin_last_name, admin_email)

    # Done
    _display_completion_summary(state, domain)
    state.mark_completed()
    success("✓ Installation complétée!")
    return 0


def _display_summary(
    domain, node, vm_name, vm_memory, vm_cores, wan_config, vxlan_config, admin_email
):
    """Afficher le résumé."""
    console.print("\n[bold]Résumé de configuration:[/bold]\n")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[bold]Domaine[/bold]", domain)
    table.add_row("[bold]Nœud[/bold]", node)
    table.add_row("[bold]VM[/bold]", f"{vm_name} ({vm_memory}MB, {vm_cores} CPU)")
    table.add_row("[bold]WAN[/bold]", wan_config["network"])
    table.add_row("[bold]VXLAN[/bold]", vxlan_config["network"])
    table.add_row("[bold]Admin[/bold]", admin_email)
    console.print(table)


def _display_completion_summary(state, domain):
    """Afficher le résumé de fin."""
    console.print("\n[bold cyan]════════════════════════════════════════[/bold cyan]")
    console.print("[bold]Installation Terminée![/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row(
        "[bold]Keycloak Console[/bold]",
        f"https://keycloak.{domain}/admin/labomatics/console/",
    )
    table.add_row(
        "[bold]Admin User[/bold]",
        f"{state.get('admin_first_name')}.{state.get('admin_last_name')}",
    )
    table.add_row(
        "[bold]Admin Password[/bold]",
        f"[yellow]{state.get('labomatics_user_password')}[/yellow]",
    )
    console.print(table)
    console.print("\n[bold cyan]════════════════════════════════════════[/bold cyan]\n")

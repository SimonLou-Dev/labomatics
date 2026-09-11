"""Installation orchestrator - main workflow."""

from rich.prompt import Confirm
from rich.table import Table

from ...commands.install.t_openwrt import OpenWRTBuilder

from ...utils.theme import console, title, success, info
from ...utils.proxmox import ProxmoxClient
from ...utils.state import InstallState
from ...utils.configgen import ClusterConfigGenerator

from .steps import (
    collect_step_1_basic_config,
    collect_step_2_proxmox_connection,
    collect_step_3_network_config,
    collect_step_4_proxmox_user,
    collect_step_5_vm_config,
    collect_step_6_download_image,
    collect_step_7_secrets,
    collect_step_8_admin_account,
    collect_step_9_ldap_radius,
)
from .vm import VMDeployer
from .network import NetworkSetup
from .ssh_manager import SSHManager
from .keycloak import KeycloakSetup
from .proxmox_oidc import ProxmoxOIDCSetup
from .ldap_setup import LdapSetup


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

    wan_config, vxlan_config, dns_servers, storage = collect_step_3_network_config(
        state
    )
    (
        labomatics_user,
        labomatics_token_id,
        labomatics_token_secret,
    ) = collect_step_4_proxmox_user(state, pve, domain)
    (
        vm_name,
        vm_memory,
        vm_cores,
        vm_password,
        ssh_pubkeys,
        ssh_privkey_path,
    ) = collect_step_5_vm_config(state)
    image_filename = collect_step_6_download_image(state, pve, node, storage)
    image_step = state.get_step(6)
    image_path: str = (
        image_step.get("image_path", "/tmp/Fedora-Cloud-Base-44.qcow2")
        if image_step
        else "/tmp/Fedora-Cloud-Base-44.qcow2"
    )
    (
        pg_root_password,
        labomatics_db_password,
        keycloak_db_password,
        keycloak_admin_password,
    ) = collect_step_7_secrets(state)

    # Récupérer les credentials des services externes (depuis step 7)
    step_7_data = state.get_step(7)
    brevo_api_key = step_7_data.get("brevo_api_key", "") if step_7_data else ""
    smtp_host = step_7_data.get("smtp_host", "") if step_7_data else ""
    smtp_port = step_7_data.get("smtp_port", "587") if step_7_data else "587"
    smtp_user = step_7_data.get("smtp_user", "") if step_7_data else ""
    smtp_password = step_7_data.get("smtp_password", "") if step_7_data else ""
    smtp_tls = step_7_data.get("smtp_tls", True) if step_7_data else True

    admin_email, admin_first_name, admin_last_name = collect_step_8_admin_account(state)
    ldap_radius_secrets = collect_step_9_ldap_radius(state)

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

    # Deploy openWRT template
    openwrt_template = OpenWRTBuilder(pve, state)
    openwrt_template.cmd_build_openwrt(storage, domain)

    # Deploy VM and infrastructure
    vm_deployer = VMDeployer(pve, node, state)
    vm_ip = vm_deployer.deploy(
        vm_name,
        vm_memory,
        vm_cores,
        storage,
        image_filename,
        wan_config,
        vm_password,
        ssh_pubkeys,
        image_path,
    )

    # Setup on VM
    network_setup = NetworkSetup(pve, domain, vm_ip, ssh_privkey_path, state)
    network_setup.setup_all(
        wan_config,
        vxlan_config,
        dns_servers,
        node,
        pg_root_password,
        labomatics_db_password,
        keycloak_db_password,
        keycloak_admin_password,
        ldap_radius_secrets,
        brevo_api_key,
        smtp_host,
        smtp_port,
        smtp_user,
        smtp_password,
        smtp_tls,
    )

    # Wait for LDAP to be ready
    LdapSetup(vm_ip).wait_ready()

    # Configure services
    kc_setup = KeycloakSetup(
        domain,
        keycloak_admin_password,
        state,
        pve,
        ldap_radius_secrets.get("base_dn"),
        ldap_radius_secrets,
    )
    kc_setup.setup(admin_first_name, admin_last_name, admin_email)

    # Update .env files with Keycloak client secret (after Keycloak setup)
    network_setup_update_env = NetworkSetup(pve, domain, vm_ip, ssh_privkey_path, state)
    try:
        network_setup_update_env.update_env_files_with_keycloak_secret()
    finally:
        network_setup_update_env.ssh.disconnect()

    oidc_setup = ProxmoxOIDCSetup(pve, domain, state)
    oidc_setup.setup(admin_first_name, admin_last_name, admin_email)

    # Generate and deploy clusterconfig.yaml
    _generate_and_deploy_clusterconfig(
        state,
        vm_ip,
        ssh_privkey_path,
        vm_name,
        proxmox_url,
        labomatics_token_id,
        labomatics_token_secret,
        storage,
        wan_config,
        vxlan_config,
        node,
        wan_iface,
    )

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

    # URLs
    console.print("[bold]🔗 URLs d'accès:[/bold]")
    console.print(f"  Frontend: [cyan]https://app.{domain}[/cyan]")
    console.print(f"  API: [cyan]https://api.{domain}/v1[/cyan]")
    console.print(
        f"  Keycloak: [cyan]https://keycloak.{domain}/admin/labomatics/console/[/cyan]"
    )
    console.print()

    # Keycloak credentials
    table.add_row(
        "[bold]Admin User[/bold]",
        f"{state.get('admin_first_name')}.{state.get('admin_last_name')}",
    )
    table.add_row(
        "[bold]Admin Password[/bold]",
        f"[yellow]{state.get('labomatics_user_password')}[/yellow]",
    )
    table.add_row(
        "[bold]Backend Service User[/bold]",
        state.get("labomatics_admin_username"),
    )
    table.add_row(
        "[bold]Backend Service Password[/bold]",
        f"[yellow]{state.get('labomatics_admin_password')}[/yellow]",
    )

    # LDAP info
    ldap_step = state.get_step(9)
    if ldap_step:
        table.add_row(
            "[bold]LDAP Base DN[/bold]",
            ldap_step.get("base_dn", "N/A"),
        )
        table.add_row(
            "[bold]LDAP Admin Password[/bold]",
            f"[yellow]{ldap_step.get('ldap_admin_password', 'N/A')}[/yellow]",
        )
        table.add_row(
            "[bold]RADIUS Shared Secret[/bold]",
            f"[yellow]{ldap_step.get('radius_shared_secret', 'N/A')}[/yellow]",
        )

    if state.get("clusterconfig_path"):
        table.add_row(
            "[bold]Cluster Config[/bold]",
            state.get("clusterconfig_path"),
        )

    console.print(table)
    console.print("\n[bold]📝 Docs:[/bold]")
    console.print("  Admin: https://docs.labomatics.io/admin/")
    console.print("  API: https://docs.labomatics.io/api/")
    console.print("\n[bold cyan]════════════════════════════════════════[/bold cyan]\n")


def _generate_and_deploy_clusterconfig(
    state,
    vm_ip,
    ssh_privkey_path,
    cluster_name,
    proxmox_url,
    labomatics_token_id,
    token_secret,
    storage,
    wan_config,
    vxlan_config,
    node,
    wan_iface,
):
    """Générer et déployer le clusterconfig.yaml sur la VM."""
    info("Génération configuration cluster...")

    # Generate YAML content
    # wan_exclusions peut être une liste ou une string (utilisateur peut fournir "172.29.20.1-172.29.20.199" ou ["..."])
    wan_exclusions = wan_config.get("exclude", [])
    if isinstance(wan_exclusions, list):
        exclusions_str = ",".join(wan_exclusions) if wan_exclusions else ""
    else:
        # Si déjà une string, l'utiliser directement
        exclusions_str = wan_exclusions if wan_exclusions else ""

    yaml_content = ClusterConfigGenerator.generate(
        cluster_name=cluster_name,
        proxmox_url=proxmox_url,
        token_id=labomatics_token_id,
        token_secret=token_secret,
        storage=storage,
        wan_name=wan_config.get("name", "wan"),
        wan_iface=wan_iface,
        wan_network=wan_config.get("network", ""),
        wan_gateway=wan_config.get("gateway", ""),
        wan_exclusions=exclusions_str,
        vxlan_name=vxlan_config.get("name", "vxlan"),
        vxlan_network=vxlan_config.get("network", ""),
        sdn_zone="labs",  # Hardcoded in network.py setup
    )

    # Deploy to VM
    ssh_client = SSHManager.connect_to_host(
        vm_ip, user="labomatics", key_filename=ssh_privkey_path
    )
    try:
        # Write YAML directly to /tmp with user permissions
        ssh_client.put_file_content("/tmp/clusterconfig.yaml", yaml_content)
        # Move to /etc/labomatics with sudo
        stdout, stderr, rc = ssh_client.exec_command(
            "sudo mv /tmp/clusterconfig.yaml /etc/labomatics/clusterconfig.yaml"
        )
        if rc != 0:
            raise RuntimeError(f"Failed to deploy clusterconfig: {stderr}")
        ssh_client.exec_command("sudo chmod 600 /etc/labomatics/clusterconfig.yaml")
        success("✓ clusterconfig.yaml déployé dans /etc/labomatics/")
        state.set("clusterconfig_path", "/etc/labomatics/clusterconfig.yaml")
    finally:
        ssh_client.disconnect()

"""Installation steps - configuration collection."""

import secrets
from rich.prompt import Prompt
from rich.console import Console

from ...utils.proxmox import ProxmoxClient
from ...utils.state import InstallState
from ...utils.cloudimage import CloudInitImageManager
from ...utils.theme import info, success, step
from .ssh_manager import SSHManager

console = Console()


def collect_step_1_basic_config(state: InstallState) -> tuple[str, str, str]:
    """Étape 1: Configuration de base (domaine, interfaces réseau)."""
    step_data = state.get_step(1)
    if step_data:
        return (
            step_data["domain"],
            step_data["network_iface"],
            step_data.get("wan_iface", "vmbr0"),
        )

    step(1, 8, "Configuration domaine et interfaces réseau")
    domain = prompt_with_retry("Domaine root", default="esgi.local")
    network_iface = prompt_with_retry("Interface réseau (ex: vmbr0)", default="vmbr0")
    wan_iface = prompt_with_retry("Interface WAN (ex: vmbr0, vmbr1)", default="vmbr0")

    state.set_step(
        1, {"domain": domain, "network_iface": network_iface, "wan_iface": wan_iface}
    )
    state.set("domain", domain)

    return domain, network_iface, wan_iface


def collect_step_2_proxmox_connection(state: InstallState) -> tuple:
    """Étape 2: Connexion Proxmox."""
    step_data = state.get_step(2)
    if step_data:
        return (
            step_data["proxmox_url"],
            step_data["proxmox_user"],
            step_data["proxmox_token_id"],
            step_data["proxmox_token_secret"],
            step_data["node"],
        )

    step(2, 8, "Connexion Proxmox")
    url = prompt_with_retry("URL Proxmox", default="https://192.168.1.1:8006")
    user = prompt_with_retry("User Proxmox", default="root@pam")
    token_id = prompt_with_retry("Token ID", default="labomatics-cli")
    token_secret = Prompt.ask("  Token secret", password=True)

    pve = ProxmoxClient(url, user, token_id, token_secret)
    nodes = pve.get_nodes()
    if not nodes:
        raise RuntimeError("Pas de nœuds Proxmox trouvés")

    console.print("\nNœuds Proxmox disponibles:")
    for i, n in enumerate(nodes, 1):
        console.print(f"  {i}. {n}")

    node_idx = int(prompt_with_retry("Sélectionner nœud (numéro)", default="1")) - 1
    node = nodes[node_idx]

    state.set_step(
        2,
        {
            "proxmox_url": url,
            "proxmox_user": user,
            "proxmox_token_id": token_id,
            "proxmox_token_secret": token_secret,
            "node": node,
        },
    )

    return url, user, token_id, token_secret, node


def collect_step_3_network_config(state: InstallState) -> tuple[dict, dict, str]:
    """Étape 3: Configuration réseau (WAN, VXLAN, DNS)."""
    step_data = state.get_step(3)
    if step_data:
        return (
            step_data["wan_config"],
            step_data["vxlan_config"],
            step_data.get("dns_servers", "8.8.8.8 8.8.4.4"),
        )

    step(3, 8, "Configuration du cluster - Réseau WAN")
    wan_name = prompt_with_retry("Nom du réseau WAN", default="esgilabs")
    wan_network = prompt_with_retry("Réseau WAN (CIDR)", default="172.16.0.0/24")
    wan_gateway = prompt_with_retry("Gateway WAN", default="172.16.0.254")
    wan_config = {
        "name": wan_name,
        "network": wan_network,
        "gateway": wan_gateway,
        "exclude": [],
    }

    step(3, 8, "Configuration du cluster - Réseau VXLAN")
    vxlan_name = prompt_with_retry("Nom de la zone VXLAN", default="esgilab")
    vxlan_network = prompt_with_retry("Réseau VXLAN (CIDR)", default="10.100.0.0/12")
    vxlan_config = {"name": vxlan_name, "network": vxlan_network, "exclude": []}

    step(3, 8, "Configuration DNS")
    dns_servers = prompt_with_retry(
        "Serveurs DNS (espace-séparé)", default="8.8.8.8 8.8.4.4"
    )

    state.set_step(
        3,
        {
            "wan_config": wan_config,
            "vxlan_config": vxlan_config,
            "dns_servers": dns_servers,
        },
    )

    return wan_config, vxlan_config, dns_servers


def collect_step_4_proxmox_user(
    state: InstallState, pve: ProxmoxClient, domain: str
) -> tuple[str, str]:
    """Étape 4: Création user Proxmox et token."""
    step_data = state.get_step(4)
    if step_data:
        return step_data["labomatics_user"], step_data["labomatics_token_secret"]

    step(4, 8, "Création user Proxmox et token")
    user_id = "labomatics-cli@pve"
    password = secrets.token_urlsafe(16)

    try:
        pve.create_user(user_id, password, comment="labomatics CLI user")
    except Exception as e:
        if "already exists" not in str(e):
            raise

    pve.set_acl("/", user_id, "PVEAdmin")
    token_data = pve.create_token(user_id, "labomatics-token")

    state.set_step(
        4,
        {
            "labomatics_user": user_id,
            "labomatics_token_secret": token_data["value"],
        },
    )

    return user_id, token_data["value"]


def collect_step_5_vm_config(state: InstallState) -> tuple:
    """Étape 5: Configuration VM et clés SSH."""
    step_data = state.get_step(5)
    if step_data and "ssh_pubkeys" in step_data:
        return (
            step_data["vm_name"],
            step_data["vm_memory"],
            step_data["vm_cores"],
            step_data["vm_storage"],
            step_data["vm_password"],
            step_data["ssh_pubkeys"],
            step_data["ssh_privkey_path"],
        )

    step(5, 8, "Configuration VM et clés SSH")
    vm_name = prompt_with_retry("Nom de la VM", default="labomatics")
    vm_memory = int(prompt_with_retry("Mémoire (MB)", default="8192"))
    vm_cores = int(prompt_with_retry("Cores CPU", default="4"))
    vm_storage = prompt_with_retry("Storage (ex: local-lvm)", default="local-lvm")
    vm_password = Prompt.ask("  Password labomatics", password=True)

    ssh_pubkeys = SSHManager.collect_ssh_keys()
    ssh_privkey_path, _ = SSHManager.get_or_generate_cli_key()

    state.set_step(
        5,
        {
            "vm_name": vm_name,
            "vm_memory": vm_memory,
            "vm_cores": vm_cores,
            "vm_storage": vm_storage,
            "vm_password": vm_password,
            "ssh_pubkeys": ssh_pubkeys,
            "ssh_privkey_path": ssh_privkey_path,
        },
    )

    return (
        vm_name,
        vm_memory,
        vm_cores,
        vm_storage,
        vm_password,
        ssh_pubkeys,
        ssh_privkey_path,
    )


def collect_step_6_download_image(
    state: InstallState, pve: ProxmoxClient, node: str, storage: str
) -> str:
    """Étape 6: Téléchargement image cloud-init."""
    step(6, 8, "Téléchargement image cloud-init")
    image_type = "fedora-server"
    image_info = CloudInitImageManager.IMAGES[image_type]
    image_filename = image_info["filename"]

    # Download to Proxmox storage
    info(f"Téléchargement {image_filename}...")
    pve.download_iso_to_storage(
        node, storage, image_info["url"], image_filename, content_type="import"
    )
    success(f"Image téléchargée: {image_filename}")

    state.set_step(6, {"image_filename": image_filename})
    return image_filename


def collect_step_7_secrets(state: InstallState) -> tuple[str, str, str, str]:
    """Étape 7: Génération des secrets."""
    step_data = state.get_step(7)
    if step_data:
        return (
            step_data["pg_root_password"],
            step_data["labomatics_db_password"],
            step_data["keycloak_db_password"],
            step_data["keycloak_admin_password"],
        )

    step(7, 8, "Génération des secrets")
    pg_root_password = secrets.token_urlsafe(16)
    labomatics_db_password = secrets.token_urlsafe(16)
    keycloak_db_password = secrets.token_urlsafe(16)
    keycloak_admin_password = secrets.token_urlsafe(16)
    success("Secrets générés")

    state.set_step(
        7,
        {
            "pg_root_password": pg_root_password,
            "labomatics_db_password": labomatics_db_password,
            "keycloak_db_password": keycloak_db_password,
            "keycloak_admin_password": keycloak_admin_password,
        },
    )

    return (
        pg_root_password,
        labomatics_db_password,
        keycloak_db_password,
        keycloak_admin_password,
    )


def collect_step_8_admin_account(state: InstallState) -> tuple[str, str, str]:
    """Étape 8: Compte administrateur Keycloak."""
    step_data = state.get_step(8)
    if step_data:
        return (
            step_data["admin_email"],
            step_data["admin_first_name"],
            step_data["admin_last_name"],
        )

    step(8, 8, "Compte administrateur Keycloak")
    admin_email = prompt_with_retry("Email administrateur")
    admin_first_name = prompt_with_retry("Prénom")
    admin_last_name = prompt_with_retry("Nom")

    state.set_step(
        8,
        {
            "admin_email": admin_email,
            "admin_first_name": admin_first_name,
            "admin_last_name": admin_last_name,
        },
    )

    return admin_email, admin_first_name, admin_last_name


def prompt_with_retry(
    prompt_text: str, default: str = None, max_retries: int = 3
) -> str:
    """Prompt avec retry."""
    for _ in range(max_retries):
        value = Prompt.ask(f"  {prompt_text}", default=default)
        if value or default:
            return value or default
    raise RuntimeError(f"Impossible de récupérer: {prompt_text}")

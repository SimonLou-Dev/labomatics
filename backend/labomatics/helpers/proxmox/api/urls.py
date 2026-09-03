"""URLs de l'API Proxmox."""

BASE = "/api2/json"

# ── Cluster ──────────────────────────────────────────────────────────────────
CLUSTER_RESOURCES = f"{BASE}/cluster/resources"

# ── Nodes ────────────────────────────────────────────────────────────────────
NODES = f"{BASE}/nodes"


def node_path(node: str) -> str:
    """Construit le chemin d'un nœud."""
    return f"{NODES}/{node}"


def node_tasks(node: str, task_id: str) -> str:
    """Chemin pour une tâche sur un nœud."""
    return f"{node_path(node)}/tasks/{task_id}"


def node_task_status(node: str, task_id: str) -> str:
    """Chemin du statut d'une tâche."""
    return f"{node_tasks(node, task_id)}/status"


def node_task_logs(node: str, task_id: str) -> str:
    """Chemin des logs d'une tâche."""
    return f"{node_tasks(node, task_id)}/log"


# ── VMs QEMU ─────────────────────────────────────────────────────────────────
def qemu_vm_path(node: str, vmid: int) -> str:
    """Chemin d'une VM QEMU."""
    return f"{node_path(node)}/qemu/{vmid}"


def qemu_config(node: str, vmid: int) -> str:
    """Chemin de la config d'une VM QEMU."""
    return f"{qemu_vm_path(node, vmid)}/config"


def qemu_clone(node: str, vmid: int) -> str:
    """Chemin pour cloner une VM QEMU."""
    return f"{qemu_vm_path(node, vmid)}/clone"


def qemu_status_start(node: str, vmid: int) -> str:
    """Chemin pour démarrer une VM QEMU."""
    return f"{qemu_vm_path(node, vmid)}/status/start"


# ── Access (Users, Tokens, ACLs) ─────────────────────────────────────────────
ACCESS = f"{BASE}/access"
ACCESS_USERS = f"{ACCESS}/users"
ACCESS_ACL = f"{ACCESS}/acl"


def access_user(userid: str) -> str:
    """Chemin d'un utilisateur."""
    return f"{ACCESS_USERS}/{userid}"


def access_user_tokens(userid: str) -> str:
    """Chemin de la liste des tokens d'un utilisateur."""
    return f"{access_user(userid)}/token"


def access_user_token(userid: str, token_name: str) -> str:
    """Chemin d'un token utilisateur."""
    return f"{access_user(userid)}/token/{token_name}"


# ── Pools ────────────────────────────────────────────────────────────────────
POOLS = f"{BASE}/pools"


def pool_path(pool_name: str) -> str:
    """Chemin d'un pool."""
    return f"{POOLS}/{pool_name}"


# ── SDN (Software Defined Network) ───────────────────────────────────────────
SDN = f"{BASE}/cluster/sdn"
SDN_ZONES = f"{SDN}/zones"
SDN_VNETS = f"{SDN}/vnets"


def sdn_zone(zone_name: str) -> str:
    """Chemin d'une zone SDN."""
    return f"{SDN_ZONES}/{zone_name}"


def sdn_vnet(vnet_name: str) -> str:
    """Chemin d'un VNet."""
    return f"{SDN_VNETS}/{vnet_name}"


def sdn_vnet_subnets(vnet_name: str) -> str:
    """Chemin des subnets d'un VNet."""
    return f"{sdn_vnet(vnet_name)}/subnets"


def sdn_vnet_subnet(vnet_name: str, subnet: str) -> str:
    """Chemin d'un subnet spécifique."""
    return f"{sdn_vnet_subnets(vnet_name)}/{subnet}"


# ── Version ──────────────────────────────────────────────────────────────────
VERSION = f"{BASE}/version"

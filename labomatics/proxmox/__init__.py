"""
Package ``labomatics.proxmox`` — couche d'accès à l'API Proxmox.

Toutes les fonctions publiques sont re-exportées ici pour permettre des imports
directs depuis ``labomatics.proxmox`` :

    from labomatics.proxmox import connect, pick_node, create_pool
"""

from .acl import (
    create_proxmox_user,
    delete_acl,
    delete_proxmox_user,
    delete_student_acls,
    set_acl,
    set_student_acls,
    user_exists,
)
from .client import POOL_MARKER, connect
from .pools import (
    add_vm_to_pool,
    create_pool,
    delete_pool,
    get_pool_lxcs,
    get_pool_vms,
    list_managed_pools,
    set_pool_limits,
)
from .sdn import (
    apply_sdn,
    check_sdn_zone_exists,
    create_vnet,
    delete_vnet,
    list_vnets_in_zone,
)
from .tasks import wait_for_task
from .vms import (
    find_vm_node,
    get_vm_disk_size_gb,
    get_vm_vxlan_subnet,
    get_vm_wan_ip,
    pick_node,
    vm_exists,
)

__all__ = [
    # client
    "POOL_MARKER",
    "connect",
    # tasks
    "wait_for_task",
    # vms
    "vm_exists",
    "find_vm_node",
    "pick_node",
    "get_vm_wan_ip",
    "get_vm_vxlan_subnet",
    "get_vm_disk_size_gb",
    # pools
    "list_managed_pools",
    "create_pool",
    "delete_pool",
    "add_vm_to_pool",
    "get_pool_vms",
    "get_pool_lxcs",
    "set_pool_limits",
    # sdn
    "check_sdn_zone_exists",
    "list_vnets_in_zone",
    "create_vnet",
    "delete_vnet",
    "apply_sdn",
    # acl
    "user_exists",
    "create_proxmox_user",
    "delete_proxmox_user",
    "set_acl",
    "delete_acl",
    "set_student_acls",
    "delete_student_acls",
]

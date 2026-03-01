"""
esgilabs — Orchestrateur Proxmox piloté par CSV étudiant.

Ce package expose les primitives principales pour être utilisé comme bibliothèque
ou via le CLI ``python -m esgilabs``.

Structure du package :

- :mod:`.config`      — modèles Pydantic et chargement de la configuration
- :mod:`.students`    — dataclass :class:`~.students.Student` et chargement CSV
- :mod:`.diff`        — calcul et affichage des différences CSV ↔ Proxmox
- :mod:`.credentials` — gestion du CSV credentials étudiants
- :mod:`.deploy`      — déploiement et destruction des VMs/LXC
- :mod:`.proxmox`     — couche d'accès à l'API Proxmox (sous-package)
"""

from .config import InfraConfig, ProxmoxSettings, load_config, load_proxmox_settings
from .students import Student, load_students
from .diff import compute_diff, print_diff
from .credentials import load_credentials, save_credentials, generate_password
from .deploy import deploy_student, destroy_student, destroy_lxc
from .proxmox import (
    # Connexion
    connect,
    POOL_MARKER,
    # Tâches
    wait_for_task,
    # VMs
    vm_exists,
    find_vm_node,
    pick_node,
    # Pools
    list_managed_pools,
    create_pool,
    delete_pool,
    add_vm_to_pool,
    get_pool_vms,
    get_pool_lxcs,
    # SDN
    check_sdn_zone_exists,
    list_vnets_in_zone,
    create_vnet,
    delete_vnet,
    apply_sdn,
    # ACL / Utilisateurs
    user_exists,
    create_proxmox_user,
    delete_proxmox_user,
    set_acl,
    delete_acl,
    set_student_acls,
    delete_student_acls,
)

__all__ = [
    # config
    "InfraConfig",
    "ProxmoxSettings",
    "load_config",
    "load_proxmox_settings",
    # students
    "Student",
    "load_students",
    # diff
    "compute_diff",
    "print_diff",
    # credentials
    "load_credentials",
    "save_credentials",
    "generate_password",
    # deploy
    "deploy_student",
    "destroy_student",
    "destroy_lxc",
    # proxmox — connexion
    "connect",
    "POOL_MARKER",
    # proxmox — tâches
    "wait_for_task",
    # proxmox — vms
    "vm_exists",
    "find_vm_node",
    "pick_node",
    # proxmox — pools
    "list_managed_pools",
    "create_pool",
    "delete_pool",
    "add_vm_to_pool",
    "get_pool_vms",
    "get_pool_lxcs",
    # proxmox — sdn
    "check_sdn_zone_exists",
    "list_vnets_in_zone",
    "create_vnet",
    "delete_vnet",
    "apply_sdn",
    # proxmox — acl
    "user_exists",
    "create_proxmox_user",
    "delete_proxmox_user",
    "set_acl",
    "delete_acl",
    "set_student_acls",
    "delete_student_acls",
]

#!/usr/bin/env python3
"""
Déploiement et destruction des VMs OpenWrt et conteneurs LXC par étudiant.

Sélection automatique des nœuds
---------------------------------
- Nœud source : nœud hébergeant la template (``find_vm_node()``)
- Nœud cible : nœud avec le plus de mémoire libre (``pick_node()``)

La template doit se trouver sur un stockage partagé (Ceph/NFS/ZFS) accessible
depuis tous les nœuds du cluster.

Allocation IP
-------------
Les IPs WAN et subnets VXLAN sont alloués dynamiquement depuis Proxmox
(lecture des ipconfig0 des VMs existantes). Voir :mod:`labomatics.ip_pool`.

Flavors
-------
Les limites de ressources (CPU/RAM/disk) sont appliquées sur le pool Proxmox
via l'API native. Proxmox retournera 403 si l'étudiant tente de démarrer
une VM dépassant ces limites.
"""

from typing import TYPE_CHECKING

from proxmoxer import ProxmoxAPI
from rich.console import Console

from .proxmox import (
    add_vm_to_pool,
    find_vm_node,
    get_pool_lxcs,
    get_pool_vms,
    pick_node,
    set_pool_limits,
    vm_exists,
    wait_for_task,
)

if TYPE_CHECKING:
    from .config import InfraConfig
    from .students import Student

console = Console()


def deploy_student(
    proxmox: ProxmoxAPI,
    config: "InfraConfig",
    student: "Student",
) -> None:
    """Clone le template OpenWrt, configure cloud-init et démarre la VM.

    Si une VM avec le même VMID existe déjà, la fonction retourne immédiatement
    (idempotent).

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure.
        student: Étudiant pour lequel déployer la VM.
    """
    from .ip_pool import allocate_vxlan_subnet, allocate_wan_ip

    storage = config.openwrt.storage
    template_id = config.openwrt.template_vmid
    vmid_start = config.openwrt.vmid_start
    vmid = student.vmid(vmid_start)
    name = student.vm_name()
    wan_bridge = config.openwrt.wan_bridge
    wan_gateway = config.openwrt.network.wan_pool.gateway
    wan_prefix = config.openwrt.network.wan_pool.network.split("/")[1]

    if vm_exists(proxmox, vmid):
        console.print(f"  [yellow]⚠  {name:25} vmid={vmid} — déjà déployé, ignoré[/yellow]")
        return

    # Allouer les IPs dynamiquement depuis Proxmox
    wan_ip = allocate_wan_ip(proxmox, config)
    vxlan_gw, vxlan_subnet = allocate_vxlan_subnet(proxmox, config)
    vnet_bridge = student.vnet_name()

    # Nœud source (héberge la template) + nœud cible (le plus libre)
    source_node = find_vm_node(proxmox, template_id)
    if source_node is None:
        raise RuntimeError(f"Template VMID {template_id} introuvable sur le cluster")
    target_node = pick_node(proxmox)

    # Clone complet depuis la template (stockage partagé requis)
    task = proxmox.nodes(source_node).qemu(template_id).clone.post(
        newid=vmid,
        name=name,
        full=1,
        storage=storage,
        target=target_node,
        pool=student.pool_name(),
    )
    wait_for_task(proxmox, source_node, task)

    # Configuration cloud-init NoCloud
    proxmox.nodes(target_node).qemu(vmid).config.put(
        cores=2,
        memory=512,
        ide2=f"{storage}:cloudinit",
        citype="nocloud",
        ipconfig0=f"ip={wan_ip}/{wan_prefix},gw={wan_gateway}",
        ipconfig1=f"ip={vxlan_gw}/24",
        serial0="socket",
        vga="serial0",
        net0=f"virtio,bridge={wan_bridge}",
        net1=f"virtio,bridge={vnet_bridge}",
        onboot=1,
    )

    # Démarrage de la VM
    task = proxmox.nodes(target_node).qemu(vmid).status.start.post()
    wait_for_task(proxmox, target_node, task)

    console.print(
        f"  [green]✓ {name:25} vmid={vmid}  node={target_node}  "
        f"WAN {wan_ip}  VXLAN {vxlan_subnet}[/green]"
    )


def apply_pool_flavor(
    proxmox: ProxmoxAPI,
    config: "InfraConfig",
    student: "Student",
) -> None:
    """Applique les limites de ressources du flavor sur le pool Proxmox natif.

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure.
        student: Étudiant dont le flavor est à appliquer.
    """
    flavor = config.get_flavor(student.flavor)
    try:
        set_pool_limits(
            proxmox,
            student.pool_name(),
            max_cpu=flavor.cpu,
            max_ram_mb=flavor.ram,
            max_disk_gb=flavor.disk,
        )
    except Exception as e:
        console.print(f"  [yellow]⚠  Quotas pool {student.pool_name()} : {e}[/yellow]")


def destroy_student(
    proxmox: ProxmoxAPI,
    node: str,
    vmid: int,
    vm_name: str,
) -> None:
    """Arrête et supprime une VM QEMU (y compris les templates).

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nœud Proxmox hébergeant la VM.
        vmid: Identifiant de la VM.
        vm_name: Nom de la VM (pour les messages de log).
    """
    try:
        proxmox.nodes(node).qemu(vmid).status.current.get()
    except Exception:
        console.print(f"  [yellow]⚠  {vm_name:25} vmid={vmid} — introuvable, ignoré[/yellow]")
        return

    try:
        task_stop = proxmox.nodes(node).qemu(vmid).status.stop.post()
        wait_for_task(proxmox, node, task_stop)
    except Exception:
        pass  # VM peut-être déjà arrêtée ou template

    task = proxmox.nodes(node).qemu(vmid).delete(purge=1)
    wait_for_task(proxmox, node, task)

    console.print(f"  [red]✖ {vm_name:25} vmid={vmid} — VM supprimée[/red]")


def destroy_lxc(
    proxmox: ProxmoxAPI,
    node: str,
    vmid: int,
    lxc_name: str,
) -> None:
    """Arrête et supprime un conteneur LXC.

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nœud Proxmox hébergeant le conteneur.
        vmid: Identifiant du conteneur LXC.
        lxc_name: Nom du conteneur (pour les messages de log).
    """
    try:
        proxmox.nodes(node).lxc(vmid).status.current.get()
    except Exception:
        console.print(f"  [yellow]⚠  {lxc_name:25} vmid={vmid} — LXC introuvable, ignoré[/yellow]")
        return

    try:
        task_stop = proxmox.nodes(node).lxc(vmid).status.stop.post()
        wait_for_task(proxmox, node, task_stop)
    except Exception:
        pass

    task = proxmox.nodes(node).lxc(vmid).delete()
    wait_for_task(proxmox, node, task)

    console.print(f"  [red]✖ {lxc_name:25} vmid={vmid} — LXC supprimé[/red]")


def destroy_all_pool_members(proxmox: ProxmoxAPI, pool_name: str) -> None:
    """Détruit toutes les VMs QEMU et LXC d'un pool (y compris les templates).

    Args:
        proxmox: Client API Proxmox authentifié.
        pool_name: Nom du pool à vider.
    """
    try:
        for member in get_pool_vms(proxmox, pool_name):
            vmid = member.get("vmid")
            node = member.get("node")
            if vmid and node:
                destroy_student(proxmox, node, vmid, member.get("name", str(vmid)))
    except Exception:
        pass

    try:
        for member in get_pool_lxcs(proxmox, pool_name):
            vmid = member.get("vmid")
            node = member.get("node")
            if vmid and node:
                destroy_lxc(proxmox, node, vmid, member.get("name", str(vmid)))
    except Exception:
        pass

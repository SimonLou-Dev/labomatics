#!/usr/bin/env python3
"""
Déploiement et destruction des VMs OpenWrt et conteneurs LXC par étudiant.

Ce module contient la logique de haut niveau pour créer et supprimer les
ressources Proxmox d'un étudiant. Il s'appuie sur le package
:mod:`esgilabs.proxmox` pour toutes les interactions avec l'API.

Sélection automatique du nœud
-------------------------------
Plutôt que de cibler un nœud fixe, :func:`deploy_student` appelle
:func:`~esgilabs.proxmox.pick_node` pour sélectionner dynamiquement le nœud
avec le plus de mémoire libre. La template OpenWrt **doit donc se trouver sur
un stockage partagé** (Ceph, NFS, ZFS replication…) accessible depuis tous
les nœuds du cluster.

Pour la destruction, le nœud est lu depuis les métadonnées du membre de pool
(champ ``node``), ce qui permet de gérer des VMs réparties sur plusieurs nœuds.
"""

from typing import TYPE_CHECKING

from proxmoxer import ProxmoxAPI
from rich.console import Console

from .proxmox import (
    add_vm_to_pool,
    pick_node,
    vm_exists,
    wait_for_task,
)

if TYPE_CHECKING:
    from .students import Student

console = Console()


def deploy_student(
    proxmox: ProxmoxAPI,
    config,
    student: "Student",
) -> None:
    """Clone le template OpenWrt, configure cloud-init et démarre la VM.

    La VM est ajoutée au pool étudiant après démarrage. Si une VM avec le
    même VMID existe déjà (exécution idempotente), la fonction retourne
    immédiatement sans rien modifier.

    Le nœud de déploiement est sélectionné automatiquement parmi les nœuds
    en ligne via :func:`~esgilabs.proxmox.pick_node`.

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure (:class:`~esgilabs.config.InfraConfig`).
        student: Étudiant pour lequel déployer la VM.

    Raises:
        RuntimeError: Si aucun nœud n'est disponible ou si une tâche Proxmox échoue.
    """
    storage = config.openwrt.storage
    template_id = config.openwrt.template_vmid
    vmid = student.vmid(config.openwrt.vmid_start)
    name = student.vm_name()

    wan_subnet = config.openwrt.network.wan_subnet
    wan_gateway = config.openwrt.network.wan_gateway
    vxlan_pool = config.openwrt.network.vxlan_pool

    wan_ip = student.wan_ip(wan_subnet)
    wan_prefix = wan_subnet.split("/")[1]
    vxlan_gw = student.vxlan_gateway(vxlan_pool)
    vnet_bridge = student.vnet_name()

    if vm_exists(proxmox, vmid):
        console.print(f"  [yellow]⚠  {name:25} vmid={vmid} — déjà déployé, ignoré[/yellow]")
        return

    # Sélection automatique du nœud avec le plus de mémoire libre
    node = pick_node(proxmox)

    # Clone complet depuis la template (stockage partagé requis)
    task = proxmox.nodes(node).qemu(template_id).clone.post(
        newid=vmid,
        name=name,
        full=1,
        storage=storage,
    )
    wait_for_task(proxmox, node, task)

    # Configuration cloud-init NoCloud
    # - net0 : WAN (vmbr0, IP fixe)
    # - net1 : LAN VXLAN (VNet SDN de l'étudiant, IP = gateway du subnet)
    proxmox.nodes(node).qemu(vmid).config.put(
        ide2=f"{storage}:cloudinit",
        citype="nocloud",
        ipconfig0=f"ip={wan_ip}/{wan_prefix},gw={wan_gateway}",
        ipconfig1=f"ip={vxlan_gw}/24",
        serial0="socket",
        vga="serial0",
        net0="virtio,bridge=vmbr0",
        net1=f"virtio,bridge={vnet_bridge}",
        onboot=1,
    )

    # Démarrage de la VM
    proxmox.nodes(node).qemu(vmid).status.start.post()

    # Ajout au pool étudiant (pour les droits Proxmox)
    add_vm_to_pool(proxmox, student.pool_name(), vmid)

    console.print(
        f"  [green]✓ {name:25} vmid={vmid}  node={node}  "
        f"WAN {wan_ip}  VXLAN {student.vxlan_subnet(vxlan_pool)}[/green]"
    )


def destroy_student(
    proxmox: ProxmoxAPI,
    node: str,
    vmid: int,
    vm_name: str,
) -> None:
    """Arrête et supprime la VM QEMU d'un étudiant.

    La suppression est purgée (``purge=1``) pour nettoyer les jobs de
    réplication et les sauvegardes associées.

    Le pool et le VNet sont supprimés par l'appelant (:mod:`__main__`)
    après cette étape, une fois que toutes les ressources du pool sont vides.

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nœud Proxmox hébergeant la VM (récupéré depuis les métadonnées du pool).
        vmid: Identifiant de la VM à supprimer.
        vm_name: Nom de la VM (pour les messages de log).
    """
    try:
        proxmox.nodes(node).qemu(vmid).status.current.get()
    except Exception:
        console.print(f"  [yellow]⚠  {vm_name:25} vmid={vmid} — introuvable, ignoré[/yellow]")
        return

    # Arrêt forcé — on attend la fin de la tâche avant de supprimer
    try:
        task_stop = proxmox.nodes(node).qemu(vmid).status.stop.post()
        wait_for_task(proxmox, node, task_stop)
    except Exception:
        pass  # La VM était peut-être déjà arrêtée

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

    Le pool est supprimé par l'appelant (:mod:`__main__`) après cette étape.

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nœud Proxmox hébergeant le conteneur.
        vmid: Identifiant du conteneur LXC à supprimer.
        lxc_name: Nom du conteneur (pour les messages de log).
    """
    try:
        proxmox.nodes(node).lxc(vmid).status.current.get()
    except Exception:
        console.print(f"  [yellow]⚠  {lxc_name:25} vmid={vmid} — LXC introuvable, ignoré[/yellow]")
        return

    # Arrêt forcé — on attend la fin de la tâche avant de supprimer
    try:
        task_stop = proxmox.nodes(node).lxc(vmid).status.stop.post()
        wait_for_task(proxmox, node, task_stop)
    except Exception:
        pass  # Le LXC était peut-être déjà arrêté

    task = proxmox.nodes(node).lxc(vmid).delete()
    wait_for_task(proxmox, node, task)

    console.print(f"  [red]✖ {lxc_name:25} vmid={vmid} — LXC supprimé[/red]")

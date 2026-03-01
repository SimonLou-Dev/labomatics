#!/usr/bin/env python3
"""
Utilitaires pour les VMs QEMU : existence, localisation et sélection de nœud.

Le déploiement est distribué : plutôt que de cibler un nœud fixe, le script
interroge le cluster et sélectionne automatiquement le nœud avec le plus de
mémoire libre (:func:`pick_node`). La template OpenWrt doit donc se trouver
sur un **stockage partagé** accessible depuis tous les nœuds.
"""

from proxmoxer import ProxmoxAPI


def pick_node(proxmox: ProxmoxAPI) -> str:
    """Sélectionne le nœud du cluster avec le plus de mémoire disponible.

    Seuls les nœuds avec le statut ``online`` sont pris en compte.

    Args:
        proxmox: Client API Proxmox authentifié.

    Returns:
        Nom du nœud sélectionné (ex. ``"pve-a-1"``).

    Raises:
        RuntimeError: Si aucun nœud n'est en ligne dans le cluster.
    """
    nodes = proxmox.nodes.get()
    online = [n for n in nodes if n.get("status") == "online"]
    if not online:
        raise RuntimeError("Aucun nœud Proxmox disponible dans le cluster")
    return max(online, key=lambda n: n.get("maxmem", 0) - n.get("mem", 0))["node"]


def vm_exists(proxmox: ProxmoxAPI, vmid: int) -> bool:
    """Vérifie si une VM (QEMU ou LXC) existe sur le cluster.

    La recherche porte sur **tous les nœuds** via l'API cluster/resources,
    sans avoir besoin de connaître le nœud à l'avance.

    Args:
        proxmox: Client API Proxmox authentifié.
        vmid: Identifiant de la VM à rechercher.

    Returns:
        ``True`` si la VM existe, ``False`` sinon.
    """
    resources = proxmox.cluster.resources.get(type="vm")
    return any(int(r.get("vmid", -1)) == vmid for r in resources)


def find_vm_node(proxmox: ProxmoxAPI, vmid: int) -> str | None:
    """Retourne le nom du nœud hébergeant une VM donnée.

    Args:
        proxmox: Client API Proxmox authentifié.
        vmid: Identifiant de la VM à localiser.

    Returns:
        Nom du nœud (ex. ``"pve-a-2"``), ou ``None`` si la VM est introuvable.
    """
    resources = proxmox.cluster.resources.get(type="vm")
    for r in resources:
        if int(r.get("vmid", -1)) == vmid:
            return r.get("node")
    return None

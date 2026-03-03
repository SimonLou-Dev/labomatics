#!/usr/bin/env python3
"""
Utilitaires pour les VMs QEMU : existence, localisation, sélection de nœud,
et lecture de la configuration réseau cloud-init.
"""

import re

from proxmoxer import ProxmoxAPI


def pick_node(proxmox: ProxmoxAPI) -> str:
    """Sélectionne le nœud du cluster avec le plus de mémoire disponible.

    Raises:
        RuntimeError: Si aucun nœud n'est en ligne.
    """
    nodes = proxmox.nodes.get()
    online = [n for n in nodes if n.get("status") == "online"]
    if not online:
        raise RuntimeError("Aucun nœud Proxmox disponible dans le cluster")
    return max(online, key=lambda n: n.get("maxmem", 0) - n.get("mem", 0))["node"]


def vm_exists(proxmox: ProxmoxAPI, vmid: int) -> bool:
    """Vérifie si une VM (QEMU ou LXC) existe sur le cluster."""
    resources = proxmox.cluster.resources.get(type="vm")
    return any(int(r.get("vmid", -1)) == vmid for r in resources)


def find_vm_node(proxmox: ProxmoxAPI, vmid: int) -> str | None:
    """Retourne le nom du nœud hébergeant une VM donnée."""
    resources = proxmox.cluster.resources.get(type="vm")
    for r in resources:
        if int(r.get("vmid", -1)) == vmid:
            return r.get("node")
    return None


def get_vm_wan_ip(proxmox: ProxmoxAPI, node: str, vmid: int) -> str | None:
    """Extrait l'IP WAN de la config cloud-init d'une VM (champ ipconfig0)."""
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()
        ipconfig0 = cfg.get("ipconfig0", "")
        m = re.search(r"ip=(\d+\.\d+\.\d+\.\d+)", ipconfig0)
        return m.group(1) if m else None
    except Exception:
        return None


def get_vm_vxlan_subnet(proxmox: ProxmoxAPI, node: str, vmid: int) -> str | None:
    """Extrait le subnet VXLAN /24 de la config cloud-init d'une VM (champ ipconfig1)."""
    try:
        cfg = proxmox.nodes(node).qemu(vmid).config.get()
        ipconfig1 = cfg.get("ipconfig1", "")
        m = re.search(r"ip=(\d+\.\d+\.\d+)\.\d+/\d+", ipconfig1)
        if m:
            return f"{m.group(1)}.0/24"
        return None
    except Exception:
        return None


def get_vm_disk_size_gb(config: dict) -> int:
    """Calcule la taille totale des disques d'une VM en GB depuis sa config Proxmox.

    Parse les clés scsi*, virtio*, ide*, sata* et extrait les tailles.
    """
    total = 0
    size_pattern = re.compile(r"size=(\d+(?:\.\d+)?)([GMKT]?)", re.IGNORECASE)
    disk_keys = {k for k in config if re.match(r"^(scsi|virtio|ide|sata)\d+$", k)}
    for key in disk_keys:
        val = str(config.get(key, ""))
        m = size_pattern.search(val)
        if m:
            size, unit = float(m.group(1)), m.group(2).upper()
            if unit == "T":
                total += int(size * 1024)
            elif unit == "G" or unit == "":
                total += int(size)
            elif unit == "M":
                total += max(1, int(size // 1024))
    return total

"""Proxmox API client pour créer et gérer les VMs."""

import requests
from typing import Dict, Any, Optional
import time


class ProxmoxClient:
    """Client Proxmox API."""

    def __init__(self, url: str, user: str, token_id: str, token_secret: str):
        """Initialiser le client."""
        self.url = url.rstrip("/")
        self.user = user
        self.token_id = token_id
        self.token_secret = token_secret
        self.session = requests.Session()
        self.session.verify = False  # TODO: proper SSL handling
        self.session.headers.update({
            "Authorization": f"PVEAPIToken={user}!{token_id}={token_secret}"
        })

    def get_nodes(self) -> list[str]:
        """Lister les nœuds disponibles."""
        resp = self.session.get(f"{self.url}/api2/json/nodes")
        resp.raise_for_status()
        return [node["node"] for node in resp.json()["data"]]

    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Obtenir le status d'un nœud."""
        resp = self.session.get(f"{self.url}/api2/json/nodes/{node}/status")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_available_vmid(self, node: str, start: int = 100) -> int:
        """Trouver un VMID disponible."""
        resp = self.session.get(f"{self.url}/api2/json/nodes/{node}/qemu")
        resp.raise_for_status()
        used_vmids = [vm["vmid"] for vm in resp.json()["data"]]
        
        vmid = start
        while vmid in used_vmids:
            vmid += 1
        return vmid

    def clone_vm(
        self,
        node: str,
        source_vmid: int,
        target_vmid: int,
        name: str,
        storage: str,
        full: bool = True,
    ) -> str:
        """Cloner une VM (template) et retourner le UPID."""
        data = {
            "vmid": target_vmid,
            "name": name,
            "full": 1 if full else 0,
            "storage": storage,
            "target": node,
        }
        resp = self.session.post(
            f"{self.url}/api2/json/nodes/{node}/qemu/{source_vmid}/clone",
            json=data,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def create_vm(
        self,
        node: str,
        vmid: int,
        name: str,
        memory: int,
        cores: int,
        storage: str,
        disk_size: int = 50,
    ) -> str:
        """Créer une nouvelle VM et retourner le UPID."""
        data = {
            "vmid": vmid,
            "name": name,
            "memory": memory,
            "cores": cores,
            "sockets": 1,
            "ostype": "l26",  # Linux kernel
            "scsi0": f"{storage}:{disk_size}",
            "net0": "virtio,bridge=vmbr0",
        }
        resp = self.session.post(
            f"{self.url}/api2/json/nodes/{node}/qemu",
            json=data,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def wait_for_task(self, node: str, upid: str, timeout: int = 300) -> bool:
        """Attendre qu'une tâche soit complète."""
        start = time.time()
        while time.time() - start < timeout:
            resp = self.session.get(f"{self.url}/api2/json/nodes/{node}/tasks/{upid}/status")
            if resp.status_code == 200:
                status = resp.json()["data"]
                if status["status"] == "stopped":
                    return status["exitstatus"] == "OK"
            time.sleep(1)
        return False

    def set_boot_order(self, node: str, vmid: int, order: str = "scsi0") -> None:
        """Définir l'ordre de boot."""
        data = {"boot": f"order={order}"}
        resp = self.session.put(
            f"{self.url}/api2/json/nodes/{node}/qemu/{vmid}/config",
            json=data,
        )
        resp.raise_for_status()

    def start_vm(self, node: str, vmid: int) -> str:
        """Démarrer une VM et retourner le UPID."""
        resp = self.session.post(f"{self.url}/api2/json/nodes/{node}/qemu/{vmid}/status/start")
        resp.raise_for_status()
        return resp.json()["data"]

    def stop_vm(self, node: str, vmid: int) -> str:
        """Arrêter une VM."""
        resp = self.session.post(f"{self.url}/api2/json/nodes/{node}/qemu/{vmid}/status/stop")
        resp.raise_for_status()
        return resp.json()["data"]

    def delete_vm(self, node: str, vmid: int) -> str:
        """Supprimer une VM."""
        resp = self.session.delete(f"{self.url}/api2/json/nodes/{node}/qemu/{vmid}")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_vm_ip(self, node: str, vmid: int, timeout: int = 60) -> Optional[str]:
        """Attendre et récupérer l'IP d'une VM."""
        start = time.time()
        while time.time() - start < timeout:
            resp = self.session.get(f"{self.url}/api2/json/nodes/{node}/qemu/{vmid}/current")
            if resp.status_code == 200:
                data = resp.json()["data"]
                if "ha" in data and "network" in data:
                    interfaces = data.get("network", {})
                    for iface, config in interfaces.items():
                        if "ipv4" in config:
                            return config["ipv4"]["address"].split("/")[0]
            time.sleep(2)
        return None

    def set_ha(self, node: str, vmid: int) -> None:
        """Ajouter la VM au HA."""
        data = {"sid": f"vm:{vmid}"}
        resp = self.session.post(f"{self.url}/api2/json/cluster/ha/resources", json=data)
        resp.raise_for_status()

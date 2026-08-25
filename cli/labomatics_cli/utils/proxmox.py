"""Client Proxmox utilisant le SDK proxmoxer."""

import time
from typing import Dict, Any, Optional
from proxmoxer import ProxmoxAPI


class ProxmoxClient:
    """Client Proxmox utilisant proxmoxer SDK."""

    def __init__(self, url: str, user: str, token_id: str, token_secret: str):
        """Initialiser le client Proxmox."""
        # Enlever https:// et le port pour proxmoxer
        host = url.replace("https://", "").replace("http://", "").split(":")[0]

        self.proxmox = ProxmoxAPI(
            host,
            user=user,
            token_name=token_id,
            token_value=token_secret,
            verify_ssl=False,  # Accept self-signed certs
        )
        self.url = url

    def get_nodes(self) -> list[str]:
        """Lister les nœuds disponibles."""
        nodes = self.proxmox.nodes.get()
        return [node["node"] for node in nodes]

    def get_cluster_name(self) -> str:
        """Récupérer le nom du cluster."""
        try:
            status = self.proxmox.cluster.status.get()
            for item in status:
                if item.get("type") == "cluster":
                    return item.get("name", "proxmox")
        except Exception:
            pass
        return "proxmox"

    def get_nodes_with_ips(self) -> Dict[str, str]:
        """Récupérer tous les nœuds avec leurs IPs via /cluster/status."""
        nodes_ips = {}
        try:
            status = self.proxmox.cluster.status.get()
            for item in status:
                if item.get("type") == "node":
                    node_name = item.get("name")
                    node_ip = item.get("ip")
                    if node_name and node_ip:
                        nodes_ips[node_name] = node_ip
        except Exception:
            pass
        return nodes_ips

    def get_node_ip(self, node: str) -> str:
        """Récupérer l'IP d'un nœud."""
        try:
            status = self.proxmox.nodes(node).status.get()
            return status.get("ip_address", "")
        except Exception:
            return ""

    def get_node_config(self, node: str) -> Dict[str, Any]:
        """Récupérer la configuration d'un nœud."""
        try:
            return self.proxmox.nodes(node).config.get()
        except Exception:
            return {}

    def get_node_fqdns(self, node: str) -> list[str]:
        """Récupérer les FQDNs d'un nœud depuis ses acmedomains."""
        fqdns = []
        config = self.get_node_config(node)
        # acmedomain0, acmedomain1, ..., acmedomain5
        for i in range(6):
            key = f"acmedomain{i}"
            if key in config:
                fqdn = config[key]
                if fqdn and fqdn not in fqdns:
                    fqdns.append(fqdn)
        return fqdns

    def get_available_vmid(self, node: str, start: int = 100) -> int:
        """Trouver un VMID disponible."""
        vms = self.proxmox.nodes(node).qemu.get()
        used_vmids = [vm["vmid"] for vm in vms]

        vmid = start
        while vmid in used_vmids:
            vmid += 1
        return vmid

    def vm_exists(self, node: str, vmid: int) -> bool:
        """Vérifier si une VM existe."""
        try:
            self.proxmox.nodes(node).qemu(vmid).status.current.get()
            return True
        except Exception:
            return False

    def find_vm_by_name(self, node: str, name: str) -> Optional[Dict[str, Any]]:
        """Trouver une VM par son nom."""
        try:
            vms = self.proxmox.nodes(node).qemu.get()
            for vm in vms:
                if vm.get("name") == name:
                    return vm
        except Exception:
            pass
        return None

    def get_vm_ip(self, node: str, vmid: int) -> Optional[str]:
        """Récupérer l'IP d'une VM depuis sa config cloud-init."""
        try:
            config = self.proxmox.nodes(node).qemu(vmid).config.get()
            ipconfig0 = config.get("ipconfig0", "")
            if "ip=" in ipconfig0:
                # Format: ip=192.168.1.100/24,gw=192.168.1.1
                ip_part = ipconfig0.split(",")[0].split("=")[1]
                return ip_part.split("/")[0]
        except Exception:
            pass
        return None

    def create_vm(
        self,
        node: str,
        vmid: int,
        name: str,
        memory: int,
        cores: int,
        storage: str,
        disk_size: int = 50,
        ciuser: str = "root",
        cicustom: str = None,
        boot_image: str = None,
        sshkeys: str = None,
        cpu: str = None,
    ) -> str:
        """Créer une VM vide et retourner le UPID."""
        # Vérifier que la VM n'existe pas déjà
        if self.vm_exists(node, vmid):
            raise RuntimeError(f"VM {vmid} existe déjà sur le nœud {node}")

        data = {
            "vmid": vmid,
            "name": name,
            "memory": memory,
            "cores": cores,
            "sockets": 1,
            "ostype": "l26",
            "bios": "ovmf",
            "efidisk0": f"{storage}:1",
            "scsihw": "virtio-scsi-pci",
            "net0": "virtio,bridge=vmbr0",
            "vga": "qxl",
            "citype": "nocloud",
            "ide2": f"{storage}:cloudinit",
            "tags": "labomatics-system",
            "onboot": 1,
        }

        if cpu:
            data["cpu"] = cpu

        # Attach boot image as scsi0 if provided
        if boot_image:
            data["scsi0"] = boot_image

        if cicustom:
            data["cicustom"] = cicustom

        if sshkeys:
            data["sshkeys"] = sshkeys

        upid = self.proxmox.nodes(node).qemu.create(**data)
        return upid

    def wait_for_task(self, node: str, upid: str, timeout: int = 300) -> bool:
        """Attendre qu'une tâche soit complète."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                status = self.proxmox.nodes(node).tasks(upid).status.get()
                if status["status"] == "stopped":
                    return status["exitstatus"] == "OK"
            except Exception:
                pass
            time.sleep(1)
        return False

    def start_vm(self, node: str, vmid: int) -> str:
        """Démarrer une VM."""
        upid = self.proxmox.nodes(node).qemu(vmid).status.start.post()
        return upid

    def stop_vm(self, node: str, vmid: int) -> str:
        """Arrêter une VM."""
        upid = self.proxmox.nodes(node).qemu(vmid).status.stop.post()
        return upid

    def delete_vm(self, node: str, vmid: int) -> str:
        """Supprimer une VM."""
        upid = self.proxmox.nodes(node).qemu(vmid).delete()
        return upid

    def resize_disk(self, node: str, vmid: int, disk: str, size: str) -> str:
        """Redimensionner un disque (ex: +20G)."""
        upid = self.proxmox.nodes(node).qemu(vmid).resize.put(disk=disk, size=size)
        return upid

    def set_cloudinit_config(
        self,
        node: str,
        vmid: int,
        username: str = "root",
        password: str = None,
        sshkeys: str = None,
        hostname: str = None,
        ipconfig0: str = None,
        ipconfig1: str = None,
        nameserver: str = None,
        ciupgrade: bool = True,
    ) -> None:
        """Définir la configuration cloud-init d'une VM."""
        data = {}

        if username:
            data["ciuser"] = username
        if password:
            data["cipassword"] = password
        if sshkeys:
            data["sshkeys"] = sshkeys
        if hostname:
            data["hostname"] = hostname
        if ipconfig0:
            data["ipconfig0"] = ipconfig0
        if ipconfig1:
            data["ipconfig1"] = ipconfig1
        if nameserver:
            data["nameserver"] = nameserver

        data["ciupgrade"] = 1 if ciupgrade else 0

        self.proxmox.nodes(node).qemu(vmid).config.put(**data)

    def user_exists(self, userid: str) -> bool:
        """Vérifier si un user existe."""
        try:
            self.proxmox.access.users(userid).get()
            return True
        except Exception:
            return False

    def create_user(self, userid: str, password: str, comment: str = "") -> None:
        """Créer un user Proxmox."""
        data = {
            "userid": userid,
            "password": password,
        }
        if comment:
            data["comment"] = comment

        self.proxmox.access.users.post(**data)

    def create_token(
        self,
        userid: str,
        tokenid: str,
        expire: int = None,
    ) -> Optional[Dict[str, Any]]:
        """Créer un token pour un user."""
        data = {}
        if expire is not None:
            data["expire"] = expire

        result = self.proxmox.access.users(userid).tokens(tokenid).post(**data)
        return result

    def set_acl(
        self,
        path: str,
        userid: str,
        role: str,
        propagate: bool = True,
    ) -> None:
        """Assigner un rôle à un user."""
        data = {
            "path": path,
            "users": userid,
            "roles": role,
            "propagate": 1 if propagate else 0,
        }
        self.proxmox.access.acl.put(**data)

    def sdn_zone_exists(self, zone: str) -> bool:
        """Vérifier si une zone SDN existe."""
        try:
            self.proxmox.cluster.sdn.zones(zone).get()
            return True
        except Exception:
            return False

    def create_sdn_zone(self, zone: str, zone_type: str = "vxlan", **kwargs) -> None:
        """Créer une zone SDN."""
        data = {
            "zone": zone,
            "type": zone_type,
        }
        data.update(kwargs)
        self.proxmox.cluster.sdn.zones.post(**data)

    def create_sdn_vnet(
        self, zone: str, vnet: str, vlanid: int = None, **kwargs
    ) -> None:
        """Créer un VNet dans une zone SDN."""
        data = {
            "vnet": vnet,
            "zone": zone,
        }
        if vlanid:
            data["vlanid"] = vlanid
        data.update(kwargs)
        self.proxmox.cluster.sdn.vnets.post(**data)

    def apply_sdn(self) -> str:
        """Appliquer la configuration SDN."""
        upid = self.proxmox.cluster.sdn.put()
        return upid

    def iso_exists(self, node: str, storage: str, filename: str) -> bool:
        """Vérifier si un fichier existe dans le storage."""
        try:
            items = self.proxmox.nodes(node).storage(storage).content.get()
            for item in items:
                content_type = item.get("content", "")
                if content_type in ("iso", "imported", "images"):
                    if filename in item.get("volid", "") or filename in item.get(
                        "name", ""
                    ):
                        return True
            return False
        except Exception:
            return False

    def download_iso_to_storage(
        self,
        node: str,
        storage: str,
        url: str,
        filename: str,
        content_type: str = "iso",
        checksum: str = None,
        checksum_algorithm: str = "sha256",
    ) -> str:
        """Télécharger un ISO/image dans le storage Proxmox."""
        data = {
            "filename": filename,
            "url": url,
        }

        if content_type:
            data["content"] = content_type

        if checksum:
            data["checksum"] = checksum
            if checksum_algorithm:
                data["checksum-algorithm"] = checksum_algorithm

        upid = self.proxmox.nodes(node).storage(storage)("download-url").post(**data)
        return upid

    def upload_cloudinit_snippet(
        self, node: str, storage: str, filename: str, content: str
    ) -> None:
        """Créer un snippet cloud-init dans snippets/ du storage partagé."""
        from pathlib import Path

        # Déterminer le chemin du storage partagé
        snippet_path = Path(f"/mnt/pve/{storage}/snippets/{filename}")

        # Créer le répertoire s'il n'existe pas
        snippet_path.parent.mkdir(parents=True, exist_ok=True)

        # Écrire le fichier
        snippet_path.write_text(content)

    def configure_cloudinit_nocloud(
        self,
        node: str,
        vmid: int,
        storage: str,
        userdata_file: str,
        network_file: str = None,
    ) -> None:
        """Configurer cloud-init NoCloud pour une VM."""
        # Format cicustom: user=storage:snippets/filename
        cicustom_parts = [f"user={storage}:snippets/{userdata_file}"]
        if network_file:
            cicustom_parts.append(f"network={storage}:snippets/{network_file}")

        data = {
            "citype": "nocloud",
            "cicustom": ",".join(cicustom_parts),
        }
        self.proxmox.nodes(node).qemu(vmid).config.put(**data)

    def enable_qemu_agent(self, node: str, vmid: int) -> None:
        """Activer l'agent QEMU pour la VM."""
        data = {"agent": "enabled=1"}
        self.proxmox.nodes(node).qemu(vmid).config.put(**data)

    def set_node_dns(
        self,
        node: str,
        dns1: str,
        dns2: str = None,
        dns3: str = None,
        search: str = None,
    ) -> None:
        """Configurer les serveurs DNS d'un nœud."""
        data = {"dns1": dns1}
        if dns2:
            data["dns2"] = dns2
        if dns3:
            data["dns3"] = dns3
        if search:
            data["search"] = search
        self.proxmox.nodes(node).dns.put(**data)

    def create_oidc_user(self, username: str, realm: str, email: str = None) -> None:
        """Créer un user OIDC dans Proxmox."""
        user_id = f"{username}@{realm}"
        data = {"userid": user_id}
        if email:
            data["email"] = email
        try:
            self.proxmox.access.users.post(**data)
        except Exception as e:
            # User might already exist, ignore
            if "already exists" not in str(e):
                raise

    def configure_oidc_realm(
        self,
        realm_name: str,
        issuer_url: str,
        client_id: str,
        client_key: str,
        username_claim: str = "preferred_username",
        scopes: str = "email profile",
        default: bool = False,
        capath: str = None,
    ) -> None:
        """Configurer un realm d'authentification OpenID Connect dans Proxmox."""
        data_create = {
            "type": "openid",
            "issuer-url": issuer_url,
            "client-id": client_id,
            "client-key": client_key,
            "username-claim": username_claim,
            "scopes": scopes,
            "autocreate": 1,
            "default": 1 if default else 0,
        }
        if capath:
            data_create["capath"] = capath

        data_update = {
            "issuer-url": issuer_url,
            "client-id": client_id,
            "client-key": client_key,
            "scopes": scopes,
            "autocreate": 1,
            "default": 1 if default else 0,
        }
        if capath:
            data_update["capath"] = capath

        try:
            self.proxmox.access.domains.post(realm=realm_name, **data_create)
        except Exception as e:
            if "already exists" in str(e):
                # Update existing realm (type and username-claim are read-only)
                self.proxmox.access.domains(realm_name).put(**data_update)
            else:
                raise

    def create_pool(self, pool_name: str) -> None:

        try:
            self.proxmox.pools(pool_name).get()
        except Exception:
            self.proxmox.pools.post(poolid=pool_name)

    def moove_vm_to_pool(self, pool_name: str, vmid: int) -> None:
        self.proxmox.pools(pool_name).put(vms=str(vmid))

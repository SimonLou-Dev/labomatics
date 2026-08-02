"""Service pour gérer Proxmox."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from proxmoxer import ProxmoxAPI

from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.security.crypto import decrypt_secret

logger = logging.getLogger(__name__)


class ProxmoxClientWrapper:
    """Wrapper du client Proxmox avec des méthodes custom."""

    def __init__(
        self, cluster_id: UUID, token_id: str, token_secret: str, url: str
    ) -> None:
        self.cluster_id = cluster_id
        self.token_id = token_id
        self.token_secret = token_secret
        self.url = url
        self.proxmox = ProxmoxAPI(
            self.url,
            user=self.token_id,
            token_name="token",
            token_value=self.token_secret,
            verify_ssl=False,
        )

    async def set_student_acl(self, student_login: str, permissions: list[str]) -> bool:
        """Configure les ACL pour un étudiant."""
        logger.info(
            f"Setting ACL for student {student_login} on cluster {self.cluster_id}"
        )
        try:
            # TODO: Implémenter les ACL Proxmox
            return True
        except Exception as e:
            logger.error(f"Failed to set ACL for {student_login}: {e}")
            raise

    async def create_vm(
        self,
        node: str,
        vmid: int,
        name: str,
        memory: int = 512,
        cores: int = 2,
        **kwargs,
    ) -> int:
        """Crée une VM Proxmox."""
        logger.info(f"Creating VM {name} ({vmid}) on node {node}")
        try:
            data = {
                "vmid": vmid,
                "name": name,
                "memory": memory,
                "cores": cores,
                "sockets": 1,
                "type": "qemu",
                **kwargs,
            }
            self.proxmox.nodes(node).qemu.create(**data)
            return vmid
        except Exception as e:
            logger.error(f"Failed to create VM {name}: {e}")
            raise

    async def upload_disk_image(
        self,
        node: str,
        storage: str,
        image_data: bytes,
        image_name: str,
    ) -> str:
        """Uploader une image disque."""
        logger.info(f"Uploading image {image_name} to {storage} on {node}")
        try:
            # Créer une image vierge
            disk_name = f"{image_name}.raw"
            size_mb = len(image_data) // (1024 * 1024) + 10  # +10MB de buffer

            # Via l'API Proxmox
            disk_id = (
                self.proxmox.nodes(node)
                .storage(storage)
                .content.create(
                    filename=disk_name,
                    size=size_mb,
                    vmid=0,  # Template
                )
            )

            # Uploader le contenu
            # Note: La méthode la plus simple est d'écrire directement dans le path de stockage
            # mais pour l'API REST, on utilise un endpoint d'upload
            logger.info(f"Disk created: {disk_id}")
            return disk_id
        except Exception as e:
            logger.error(f"Failed to upload disk image: {e}")
            raise

    async def set_vm_network(
        self,
        node: str,
        vmid: int,
        network_config: dict,
    ) -> bool:
        """Configure le réseau d'une VM."""
        logger.info(f"Configuring network for VM {vmid}")
        try:
            # Configurer les interfaces réseau
            update_data = {}
            for idx, (if_name, config) in enumerate(network_config.items()):
                update_data[f"net{idx}"] = (
                    f"virtio,bridge={config.get('bridge', 'vmbr0')}"
                )

            self.proxmox.nodes(node).qemu(vmid).config.put(**update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to configure network for VM {vmid}: {e}")
            raise

    async def create_template(self, node: str, vmid: int) -> bool:
        """Marque une VM comme template."""
        logger.info(f"Converting VM {vmid} to template")
        try:
            self.proxmox.nodes(node).qemu(vmid).template.post()
            return True
        except Exception as e:
            logger.error(f"Failed to create template from VM {vmid}: {e}")
            raise

    async def start_vm(self, node: str, vmid: int) -> bool:
        """Démarre une VM."""
        logger.info(f"Starting VM {vmid}")
        try:
            self.proxmox.nodes(node).qemu(vmid).status.current.get()
            self.proxmox.nodes(node).qemu(vmid).status.start.post()
            # Attendre que la VM démarre
            time.sleep(5)
            return True
        except Exception as e:
            logger.error(f"Failed to start VM {vmid}: {e}")
            raise

    async def stop_vm(self, node: str, vmid: int) -> bool:
        """Arrête une VM."""
        logger.info(f"Stopping VM {vmid}")
        try:
            self.proxmox.nodes(node).qemu(vmid).status.stop.post()
            return True
        except Exception as e:
            logger.error(f"Failed to stop VM {vmid}: {e}")
            raise

    async def delete_user(self, login: str) -> bool:
        """Supprime un user Proxmox."""
        logger.info(f"Deleting Proxmox user {login}")
        try:
            self.proxmox.access.users(login).delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete Proxmox user {login}: {e}")
            raise


class ProxmoxService:
    """Service pour gérer Proxmox."""

    def __init__(self, cluster_repo: ClusterRepository | None = None) -> None:
        self.cluster_repo = cluster_repo or ClusterRepository()

    async def get_client(self, cluster_id: UUID) -> ProxmoxClientWrapper:
        """Retourne un client Proxmox configuré pour un cluster."""
        cluster = await self.cluster_repo.get(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        credential = cluster.credential
        if not credential:
            raise ValueError(f"No credential found for cluster {cluster_id}")

        token_secret = decrypt_secret(credential.encrypted_token_secret)

        return ProxmoxClientWrapper(
            cluster_id=cluster_id,
            token_id=credential.token_id,
            token_secret=token_secret,
            url=cluster.url,
        )

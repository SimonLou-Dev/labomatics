"""Helper pour construire et configurer les templates OpenWRT sur Proxmox."""

from __future__ import annotations

import logging
import re
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class OpenWRTBuilderHelper:
    """Helper pour gérer les templates OpenWRT."""

    OPENWRT_RELEASES_URL = "https://downloads.openwrt.org/releases/"
    OPENWRT_DOWNLOAD_URL = (
        "https://downloads.openwrt.org/releases/{version}/targets/{target}/"
    )

    # Configuration de base pour les templates OpenWRT
    DEFAULT_VMID_TEMPLATE = 9000  # Les templates commencent à 9000
    DEFAULT_MEMORY = 512
    DEFAULT_CORES = 2
    DEFAULT_STORAGE = "local-lvm"

    def __init__(self) -> None:
        pass

    async def get_latest_openwrt_version(self) -> str:
        """Récupère la dernière version stable d'OpenWRT."""
        try:
            with urllib.request.urlopen(self.OPENWRT_RELEASES_URL, timeout=10) as resp:
                html = resp.read().decode()
            versions = re.findall(r'href="(\d+\.\d+\.\d+)/"', html)
            if not versions:
                raise RuntimeError(
                    "Impossible de récupérer la liste des versions OpenWrt"
                )
            return str(
                sorted(versions, key=lambda v: tuple(int(x) for x in v.split(".")))[-1]
            )
        except Exception as e:
            logger.error(f"Failed to get OpenWRT version: {e}")
            raise

    async def download_openwrt_image(
        self, version: str, target: str, image_name: str
    ) -> bytes:
        """Télécharge une image OpenWRT spécifique."""
        try:
            url = f"{self.OPENWRT_DOWNLOAD_URL.format(version=version, target=target)}{image_name}"
            logger.info(f"Downloading OpenWRT image from {url}")
            with urllib.request.urlopen(url, timeout=30) as resp:
                return resp.read()
        except Exception as e:
            logger.error(f"Failed to download OpenWRT image: {e}")
            raise

    async def create_template_config(
        self, cluster_name: str, network_config: dict[str, Any]
    ) -> str:
        """Crée une configuration UCI pour OpenWRT."""
        config = """
config interface 'lan'
    option type 'bridge'
    option ifname 'eth0'
    option proto 'static'
    option ipaddr '{lan_ip}'
    option netmask '{lan_netmask}'

config interface 'wan'
    option ifname 'eth1'
    option proto 'dhcp'

config interface 'student_vxlan'
    option type 'bridge'
    option proto 'static'
    option ipaddr '{vxlan_ip}'
    option netmask '255.255.255.0'

config system
    option hostname '{hostname}'
    option timezone 'UTC'

config firewall
    option syn_flood '1'
    option drop_invalid '1'
""".format(
            lan_ip=network_config.get("lan_ip", "192.168.1.1"),
            lan_netmask=network_config.get("lan_netmask", "255.255.255.0"),
            vxlan_ip=network_config.get("vxlan_ip", "10.0.0.1"),
            hostname=f"openwrt-{cluster_name}",
        )
        return config

    async def build_template(
        self,
        cluster_name: str,
        proxmox_client: Any,
        network_config: dict[str, Any],
        node: str = "pve",
        target: str = "x86/64",
        image_name: str = "openwrt-x86-64-generic-ext4-rootfs.img.gz",
    ) -> dict[str, Any]:
        """
        Construit la template OpenWRT sur un cluster Proxmox.

        Args:
            cluster_name: Nom du cluster
            proxmox_client: ProxmoxClientWrapper
            network_config: Configuration réseau
            node: Nœud Proxmox (défaut: pve)
            target: Target OpenWRT (défaut: x86/64)
            image_name: Nom de l'image à télécharger

        Returns:
            Informations sur la template créée
        """
        try:
            version = await self.get_latest_openwrt_version()
            logger.info(f"Building OpenWRT {version} template on {cluster_name}/{node}")

            # Générer un VMID unique basé sur le cluster
            vmid = self.DEFAULT_VMID_TEMPLATE + hash(cluster_name) % 100

            # 1. Télécharger l'image OpenWRT
            logger.info("Downloading OpenWRT image...")
            image_data = await self.download_openwrt_image(version, target, image_name)
            logger.info(f"Downloaded {len(image_data) / (1024*1024):.2f} MB")

            # 2. Créer une VM de base
            logger.info(f"Creating VM template {vmid}...")
            await proxmox_client.create_vm(
                node=node,
                vmid=vmid,
                name=f"openwrt-template-{cluster_name}",
                memory=self.DEFAULT_MEMORY,
                cores=self.DEFAULT_CORES,
                scsihw="virtio-scsi-pci",
                ostype="l26",
            )

            # 3. Configurer le réseau
            logger.info("Configuring network...")
            await proxmox_client.set_vm_network(
                node=node,
                vmid=vmid,
                network_config={
                    "lan": {"bridge": "vmbr0"},
                    "wan": {"bridge": "vmbr1"},
                },
            )

            # 4. Uploader l'image disque
            logger.info("Uploading disk image...")
            disk_id = await proxmox_client.upload_disk_image(
                node=node,
                storage=self.DEFAULT_STORAGE,
                image_data=image_data,
                image_name=f"openwrt-{cluster_name}-{version}",
            )

            # 5. Marquer comme template
            logger.info("Creating template...")
            await proxmox_client.create_template(node=node, vmid=vmid)

            logger.info(f"OpenWRT template successfully created: {vmid}")
            return {
                "status": "success",
                "template_id": vmid,
                "template_name": f"openwrt-template-{cluster_name}",
                "version": version,
                "cluster": cluster_name,
                "node": node,
                "disk_id": disk_id,
            }
        except Exception as e:
            logger.error(f"Failed to build OpenWRT template: {e}")
            raise

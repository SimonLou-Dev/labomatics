"""Génération du fichier de config YAML initial du cluster."""

import yaml
from typing import Optional, List

from ..models.config import (
    ClusterConfigFile,
    ClusterEntry,
    WanConfig,
    VnetConfig,
)


class ClusterConfigGenerator:
    """Génère la config YAML initiale du cluster."""

    @staticmethod
    def generate(
        cluster_name: str,
        proxmox_url: str,
        token_id: str,
        token_secret: str,
        storage: str,
        wan_name: str,
        wan_iface: str,
        wan_network: str,
        wan_gateway: str,
        wan_exclusions: str,
        vxlan_name: str,
        vxlan_network: str,
        vxlan_mtu: int = 1350,
        sdn_zone: str = None,
        vni_min: int = 1000,
        vni_max: int = 4000,
    ) -> str:
        """Générer le contenu YAML de la config avec validation Pydantic."""

        # Parse wan exclusions
        exclusions: Optional[List[str]] = None
        if wan_exclusions:
            excl_list = []
            for excl in wan_exclusions.split(","):
                excl = excl.strip()
                if excl:
                    excl_list.append(excl)
            if excl_list:
                exclusions = excl_list

        # Créer les modèles Pydantic
        wan_config = WanConfig(
            name=wan_name,
            network=wan_network,
            gateway=wan_gateway,
            exclusions=exclusions,
        )

        vnet_config = VnetConfig(
            name=vxlan_name,
            network=vxlan_network,
            mtu=vxlan_mtu,
            vni_min=vni_min,
            vni_max=vni_max,
        )

        # Format backend pour bootstrap
        cluster_data = {
            "cluster_id": None,  # Généré par la DB
            "name": cluster_name,
            "url": proxmox_url,
            "sdn_zone": sdn_zone,
            "wan_configs": [
                {
                    "ip_range_id": None,  # Généré par la DB
                    "name": wan_name,
                }
            ],
            "vnet_config": {
                "vxlan_range_id": None,  # Généré par la DB
                "name": vxlan_name,
            } if vxlan_name else None,
        }

        config_data = {
            "clusters": [cluster_data],
            "wan": [wan_config.model_dump(exclude_none=True)],
            "vnets": [vnet_config.model_dump(exclude_none=True)],
        }

        # Sérialiser en YAML
        return yaml.dump(
            config_data,
            default_flow_style=False,
            sort_keys=False,
        )

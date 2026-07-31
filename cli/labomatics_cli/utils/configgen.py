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
        )

        cluster_entry = ClusterEntry(
            name=cluster_name,
            token_id=f"root@pam!{token_id}",
            token_secret=token_secret,
            url=proxmox_url,
            storage=storage,
            wan={"name": wan_name, "iface": wan_iface},
            vnets={"name": vxlan_name},
        )

        config = ClusterConfigFile(
            kind="clusterconfig/v1",
            clusters=[cluster_entry],
            wan=[wan_config],
            vnets=[vnet_config],
        )

        # Sérialiser en YAML
        return yaml.dump(
            config.model_dump(exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
        )

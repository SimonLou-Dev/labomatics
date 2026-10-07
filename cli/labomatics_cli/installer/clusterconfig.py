"""Fichier `clusterconfig.yaml` lu par le backend au démarrage."""

from __future__ import annotations

from typing import Any

import yaml

from labomatics_cli.models.install_config import InstallConfig


class ClusterConfigBuilder:
    """Construit le YAML au format du DTO `ClusterConfigFileDTO` du backend."""

    def __init__(self, config: InstallConfig) -> None:
        """Initialise le constructeur.

        Args:
            config: Réponses du wizard (Proxmox, WAN et VXLAN renseignés).
        """
        assert config.proxmox and config.wan and config.vxlan
        self.config = config

    def data(self, token_id: str, token_secret: str) -> dict[str, Any]:
        """Structure de la configuration.

        Args:
            token_id: Identifiant complet du jeton du backend (`user@realm!nom`).
            token_secret: Secret du jeton.

        Returns:
            Les clusters, réseaux WAN et VNets ; les listes d'exclusions vides sont omises.
        """
        proxmox, wan, vxlan = self.config.proxmox, self.config.wan, self.config.vxlan
        assert proxmox and wan and vxlan
        wan_entry: dict[str, Any] = {
            "name": wan.name,
            "network": wan.network,
            "gateway": wan.gateway,
        }
        if wan.exclusions:
            wan_entry["exclusions"] = wan.exclusions
        vnet_entry: dict[str, Any] = {
            "name": vxlan.vnet_name,
            "network": vxlan.network,
            "mtu": vxlan.mtu,
            "vni_min": vxlan.vni_min,
            "vni_max": vxlan.vni_max,
        }
        if vxlan.vni_exclusions:
            vnet_entry["exclusions"] = vxlan.vni_exclusions
        return {
            "clusters": [
                {
                    "name": proxmox.cluster_name,
                    "url": proxmox.url,
                    "sdn_zone": vxlan.zone,
                    "default_storage": vxlan.storage,
                    "wan_configs": [{"name": wan.name}],
                    "vnet_config": {"name": vxlan.vnet_name},
                    "token_id": token_id,
                    "token_secret": token_secret,
                }
            ],
            "wan": [wan_entry],
            "vnets": [vnet_entry],
        }

    def render(self, token_id: str, token_secret: str) -> str:
        """Sérialise la configuration en YAML.

        Args:
            token_id: Identifiant complet du jeton du backend.
            token_secret: Secret du jeton.

        Returns:
            Le texte YAML.
        """
        return yaml.safe_dump(
            self.data(token_id, token_secret), sort_keys=False, allow_unicode=True
        )

"""Modèles Pydantic pour la configuration du cluster."""

from pydantic import BaseModel, Field
from typing import Optional, List


class WanConfig(BaseModel):
    """Configuration du réseau WAN."""

    name: str = Field(..., description="Nom du réseau WAN (ex: esgilabs)")
    network: str = Field(..., description="CIDR du réseau WAN (ex: 172.16.0.0/24)")
    gateway: str = Field(..., description="Gateway WAN (ex: 172.16.0.254)")
    exclusions: Optional[List[str]] = Field(
        None,
        description="IPs à exclure (ex: ['172.16.0.1-172.16.0.10'])",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "esgilabs",
                "network": "172.16.0.0/24",
                "gateway": "172.16.0.254",
                "exclusions": ["172.16.0.1-172.16.0.10"],
            }
        }


class VnetConfig(BaseModel):
    """Configuration d'un VNet VXLAN."""

    name: str = Field(..., description="Nom de la zone (ex: esgilab)")
    network: str = Field(..., description="CIDR du réseau VXLAN (ex: 10.100.0.0/12)")
    mtu: int = Field(1350, description="MTU du réseau VXLAN")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "esgilab",
                "network": "10.100.0.0/12",
                "mtu": 1350,
            }
        }


class ClusterEntry(BaseModel):
    """Configuration d'un cluster enregistré."""

    name: str = Field(..., description="Nom du cluster (ex: labomatics)")
    token_id: str = Field(..., description="Token ID Proxmox (ex: root@pam!labomatics)")
    token_secret: str = Field(..., description="Secret du token (sensible)")
    url: str = Field(..., description="URL Proxmox (ex: https://192.168.1.10:8006)")
    storage: str = Field(..., description="Storage par défaut (ex: local-lvm)")

    wan: dict = Field(
        ...,
        description="Référence WAN: {name: str, iface: str}",
    )
    vnets: dict = Field(
        ...,
        description="Référence VNet: {name: str}",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "labomatics",
                "token_id": "root@pam!labomatics-cli",
                "token_secret": "xxxxxxxxxxxx",
                "url": "https://192.168.1.10:8006",
                "storage": "local-lvm",
                "wan": {"name": "esgilabs", "iface": "vmbr0"},
                "vnets": {"name": "esgilab"},
            }
        }


class ClusterConfigFile(BaseModel):
    """Fichier de configuration initial du cluster (kind: clusterconfig/v1)."""

    kind: str = Field("clusterconfig/v1", description="Version du schéma")
    clusters: List[ClusterEntry] = Field(
        ...,
        description="Liste des clusters enregistrés",
    )
    wan: List[WanConfig] = Field(
        ...,
        description="Configurations WAN disponibles",
    )
    vnets: List[VnetConfig] = Field(
        ...,
        description="Configurations VNet disponibles",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "kind": "clusterconfig/v1",
                "clusters": [
                    {
                        "name": "labomatics",
                        "token_id": "root@pam!labomatics-cli",
                        "token_secret": "xxxx",
                        "url": "https://192.168.1.10:8006",
                        "storage": "local-lvm",
                        "wan": {"name": "esgilabs", "iface": "vmbr0"},
                        "vnets": {"name": "esgilab"},
                    }
                ],
                "wan": [
                    {
                        "name": "esgilabs",
                        "network": "172.16.0.0/24",
                        "gateway": "172.16.0.254",
                        "exclusions": ["172.16.0.1-172.16.0.10"],
                    }
                ],
                "vnets": [
                    {
                        "name": "esgilab",
                        "network": "10.100.0.0/12",
                        "mtu": 1350,
                    }
                ],
            }
        }

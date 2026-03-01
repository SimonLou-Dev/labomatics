#!/usr/bin/env python3
"""
Configuration management using Pydantic.
Loads credentials from .env and infrastructure settings.
"""

from pathlib import Path

from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings
from rich.console import Console
from rich.table import Table

console = Console()


class ProxmoxSettings(BaseSettings):
    """Proxmox API credentials from environment variables."""

    host: str = Field(..., description="Proxmox host/IP")
    token_id: str = Field(..., description="Token ID (user@pve!token-name)")
    token_secret: str = Field(..., description="Token secret/password")

    class Config:
        env_prefix = "PROXMOX_"
        case_sensitive = False


class NetworkConfig(BaseModel):
    """Network configuration for VXLAN and WAN."""

    zone_name: str = Field(..., description="Nom de la zone SDN VXLAN (e.g., esgilab)")
    wan_subnet: str = Field(..., description="WAN subnet (e.g., 10.255.0.0/23)")
    wan_gateway: str = Field(..., description="WAN gateway IP (e.g., 10.255.1.254)")
    vxlan_pool: str = Field(
        default="10.100.0.0/12",
        description="Pool VXLAN — les /24 par étudiant sont alloués depuis cette adresse",
    )


class OpenWrtConfig(BaseModel):
    """OpenWrt VMs configuration."""

    vmid_start: int = Field(..., description="Starting VM ID for OpenWrt instances")
    template_vmid: int = Field(..., description="Template VM ID (created by build script)")
    storage: str = Field(..., description="Shared storage pool accessible from all nodes (e.g., zfs-store)")
    students_csv: str = Field(
        default="students.csv",
        description="Chemin vers le CSV des étudiants (relatif à la racine du projet)",
    )
    template_pool: str = Field(
        default="template",
        description="Nom du pool Proxmox contenant les templates globaux (pour les ACL étudiants)",
    )
    network: NetworkConfig = Field(..., description="Network settings")


class InfraConfig(BaseModel):
    """Complete infrastructure configuration."""

    openwrt: OpenWrtConfig = Field(..., description="OpenWrt configuration")

    def display(self) -> None:
        """Display configuration using Rich."""
        console.print("\n[bold cyan]📋 Infrastructure Configuration[/bold cyan]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("OpenWrt VMID Start", str(self.openwrt.vmid_start))
        table.add_row("Template VMID", str(self.openwrt.template_vmid))
        table.add_row("Storage Pool (shared)", self.openwrt.storage)
        table.add_row("Template Pool", self.openwrt.template_pool)
        table.add_row("Students CSV", self.openwrt.students_csv)
        table.add_row("VXLAN Zone", self.openwrt.network.zone_name)
        table.add_row("WAN Subnet", self.openwrt.network.wan_subnet)
        table.add_row("WAN Gateway", self.openwrt.network.wan_gateway)
        table.add_row("VXLAN Pool", self.openwrt.network.vxlan_pool)

        console.print(table)
        console.print()


def load_config() -> InfraConfig:
    """Load infrastructure configuration from infra.yaml."""
    import json

    path = Path(__file__).parent.parent / "infra.yaml"
    if not path.exists():
        console.print(f"[red]❌ Config file not found: {path}[/red]")
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with open(path) as f:
            if path.suffix == ".json":
                data = json.load(f)
            elif path.suffix in (".yaml", ".yml"):
                import yaml
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        return InfraConfig(**data)
    except Exception as e:
        console.print(f"[red]❌ Failed to load config: {e}[/red]")
        raise


def load_proxmox_settings() -> ProxmoxSettings:
    """Load Proxmox settings from environment variables."""
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    try:
        return ProxmoxSettings()
    except Exception as e:
        console.print(f"[red]❌ Missing Proxmox credentials: {e}[/red]")
        raise

#!/usr/bin/env python3
"""
Configuration Pydantic pour labomatics.

Charge les credentials Proxmox depuis l'environnement (.env) et la
configuration de l'infrastructure depuis infra.yaml.

Ordre de recherche pour infra.yaml / .env :
1. /etc/labomatics/
2. répertoire courant
3. répertoire parent du package (dev local)
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# ── Proxmox credentials (depuis l'environnement) ──────────────────────────────


class ProxmoxSettings(BaseSettings):
    """Credentials Proxmox lus depuis les variables d'environnement."""

    host: str = Field(..., description="Proxmox host/IP")
    token_id: str = Field(..., description="Token ID (user@pve!token-name)")
    token_secret: str = Field(..., description="Token secret/password")

    model_config = {"env_prefix": "PROXMOX_", "case_sensitive": False}


# ── Réseau ────────────────────────────────────────────────────────────────────


class WanPoolConfig(BaseModel):
    network: str
    gateway: str
    exclude: list[str] = []


class VxlanPoolConfig(BaseModel):
    network: str
    exclude: list[str] = []


class NetworkConfig(BaseModel):
    zone_name: str
    wan_pool: WanPoolConfig
    vxlan_pool: VxlanPoolConfig


# ── OpenWrt ───────────────────────────────────────────────────────────────────


class OpenWrtConfig(BaseModel):
    vmid_start: int
    template_vmid: int
    storage: str
    wan_bridge: str = "vmbr0"
    students_csv: str = "students.csv"
    template_pool: str = "template"
    network: NetworkConfig


# ── Flavors ───────────────────────────────────────────────────────────────────


class FlavorConfig(BaseModel):
    """Profil de ressources (CPU/RAM/disk) pour un groupe d'étudiants.

    Les valeurs à 0 signifient « illimité ».
    """

    cpu: int = 0  # vCPU max (VMs running dans le pool)
    ram: int = 0  # MB max (VMs running)
    disk: int = 0  # GB max (toutes VMs, running ou non)


# ── Daemon quotas ─────────────────────────────────────────────────────────────


class QuotadConfig(BaseModel):
    interval: int = 30  # secondes entre chaque vérification
    action: str = "stop"  # "stop" | "alert-only"


# ── Templates ─────────────────────────────────────────────────────────────────


class TemplateProvisioningConfig(BaseModel):
    method: str = "ssh"  # "ssh" | "guest-agent"
    user: str = "root"
    commands: list[str] = []


class TemplateConfig(BaseModel):
    name: str
    vmid: int
    packer: str | None = None
    provisioning: TemplateProvisioningConfig = Field(default_factory=TemplateProvisioningConfig)


# ── Config principale ─────────────────────────────────────────────────────────


class InfraConfig(BaseModel):
    version: str = "v1"
    openwrt: OpenWrtConfig
    flavors: dict[str, FlavorConfig] = {}
    quotad: QuotadConfig = Field(default_factory=QuotadConfig)
    templates: list[TemplateConfig] = []

    def get_flavor(self, name: str) -> FlavorConfig:
        """Retourne le flavor par nom, ou le premier défini si le nom est absent."""
        if name and name in self.flavors:
            return self.flavors[name]
        return next(iter(self.flavors.values()), FlavorConfig())


# ── Loaders ───────────────────────────────────────────────────────────────────


def _find_file(filename: str) -> Path:
    """Cherche un fichier dans /etc/labomatics/, le répertoire courant, puis le parent du package."""
    candidates = [
        Path("/etc/labomatics") / filename,
        Path.cwd() / filename,
        Path(__file__).parent.parent / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Fichier introuvable : {filename}\n"
        "  Candidates: " + ", ".join(str(c) for c in candidates) + "\n"
        "  Exécutez 'labomatics init' pour créer la configuration initiale."
    )


def load_config() -> InfraConfig:
    """Charge la configuration depuis infra.yaml."""
    import yaml

    path = _find_file("infra.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return InfraConfig(**data)


def load_proxmox_settings() -> ProxmoxSettings:
    """Charge les credentials Proxmox depuis les variables d'environnement (.env)."""
    from dotenv import load_dotenv

    for candidate in [
        Path("/etc/labomatics/.env"),
        Path.cwd() / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        if candidate.exists():
            load_dotenv(candidate)
            break

    return ProxmoxSettings()  # type: ignore[call-arg]

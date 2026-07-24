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


class TemplateConfig(BaseModel):
    name: str
    vmid: int
    node: str | None = None  # nœud cible (None = pick_node automatique)
    storage_pool: str = "local-lvm"  # stockage pour le disque VM
    iso_storage_pool: str = "local"  # stockage pour télécharger l'image (type directory)
    iso_url: str  # URL de l'image cloud à télécharger
    iso_filename: str | None = None  # nom du fichier local (défaut: déduit de l'URL)
    bridge: str = "vmbr0"  # bridge réseau temporaire pendant le build
    # Surcharge par template — None = utilise TemplatesConfig.default_user / default_pass
    cloud_init_user: str | None = None
    cloud_init_password: str | None = None
    memory: int = 2048  # RAM en MB
    cores: int = 2  # vCPUs
    disk_size: str = "10G"  # taille finale du disque (ex: "10G", "20G")
    cloudinit: bool = True  # False = pas de drive cloud-init ni de boot (ex: OPNsense)
    ostype: str = "l26"  # type OS Proxmox : l26, other, freebsd, win10…
    cpu_type: str = "x86-64-v2-AES"  # type CPU Proxmox (kvm64 pour meilleure compatibilité)
    boot_timeout: int = 300  # timeout guest agent en secondes (augmenter pour Alpine)
    download_packages: bool = True  # False = désactiver virt-customize pour cette template
    extra_packages: list[str] = []  # packages supplémentaires (s'ajoutent à default_packages)


class TemplatesConfig(BaseModel):
    default_user: str = "labomatics"  # utilisateur cloud-init par défaut (toutes les templates)
    default_pass: str = "changeme"  # mot de passe cloud-init par défaut
    default_packages: list[
        str
    ] = []  # packages installés dans toutes les templates via virt-customize
    sources: list[TemplateConfig] = []


# ── TP (déploiement de travaux pratiques) ─────────────────────────────────────


class TpNicConfig(BaseModel):
    """Interface réseau supplémentaire (net1+) pour une VM de TP."""

    bridge: str
    model: str = "virtio"


class TpCloudInitConfig(BaseModel):
    """Configuration cloud-init minimale pour une VM de TP."""

    user: str | None = None
    password: str | None = None


class TpVmConfig(BaseModel):
    """Définition d'une VM à déployer dans un TP."""

    name: str
    template: int  # VMID de la template source
    memory: int = 512
    cores: int = 1
    start: bool = False  # démarrer après création
    disk_size: str | None = None  # redimensionne le disque si défini (ex: "20G")
    cloud_init: TpCloudInitConfig | None = None
    extra_nics: list[TpNicConfig] = []  # net1, net2… (net0 = LAN étudiant, toujours auto)


class TpConfig(BaseModel):
    """Configuration d'un TP : VMs à déployer par groupe d'étudiants."""

    name: str  # identifiant unique (utilisé pour le tracking via tags Proxmox)
    description: str | None = None
    tags: list[str] = []  # tags Proxmox appliqués aux VMs créées
    target_classes: list[str] | None = None  # None = tous les étudiants du CSV
    vms: list[TpVmConfig] = []


# ── Config principale ─────────────────────────────────────────────────────────


class InfraConfig(BaseModel):
    version: str = "v1"
    openwrt: OpenWrtConfig
    flavors: dict[str, FlavorConfig] = {}
    quotad: QuotadConfig = Field(default_factory=QuotadConfig)
    templates: TemplatesConfig = Field(default_factory=TemplatesConfig)

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


def load_tp_config(path: str) -> TpConfig:
    """Charge la configuration d'un TP depuis un fichier YAML."""
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TpConfig(**data)


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

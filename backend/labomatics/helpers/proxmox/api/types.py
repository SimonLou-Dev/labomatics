"""Types Pydantic pour les retours API Proxmox."""

from pydantic import BaseModel, Field


class NodeInfo(BaseModel):
    """Informations d'un nœud Proxmox."""

    node: str
    status: str
    uptime: int
    maxmem: int | None = None
    mem: int | None = None
    maxcpu: int | None = None
    cpu: float | None = None


class ClusterResource(BaseModel):
    """Ressource du cluster (VM, LXC, nœud, etc.)."""

    id: str
    type: str
    node: str | None = None
    vmid: int | None = None
    name: str | None = None
    status: str | None = None
    maxmem: int | None = None
    mem: int | None = None


class ClusterResourcesResponse(BaseModel):
    """Réponse à /cluster/resources."""

    resources: list[ClusterResource]


class TaskStatus(BaseModel):
    """Statut d'une tâche Proxmox."""

    id: str
    upid: str
    node: str
    pid: int
    pstart: int
    type: str
    status: str
    exitstatus: str | None = None
    starttime: int
    endtime: int | None = None


class TaskLog(BaseModel):
    """Ligne de log d'une tâche."""

    n: int = Field(..., description="Numéro de ligne")
    t: str = Field(..., description="Texte du log")


class QemuConfig(BaseModel):
    """Configuration d'une VM QEMU."""

    vmid: int
    name: str | None = None
    description: str | None = None
    ipconfig0: str | None = None
    ipconfig1: str | None = None
    memory: int | None = None
    cores: int | None = None
    sockets: int | None = None

    class Config:
        extra = "allow"  # Permet d'autres champs


class CloudInitConfigDTO(BaseModel):
    """Configuration cloud-init pour une VM OpenWRT."""

    cores: int = Field(default=2)
    memory: int = Field(default=512)
    storage_device: str  # ex: "local"
    wan_ip: str  # ex: "192.168.1.10"
    wan_prefix: int  # ex: 24
    wan_gateway: str  # ex: "192.168.1.1"
    vxlan_gateway_ip: str  # ex: "10.100.18.254" (dernière IP utilisable du subnet)
    wan_bridge: str = Field(default="vmbr0")
    vnet_bridge: str  # ex: "labomatics_vn100"
    tags: str = Field(default="labomatics-system")
    onboot: bool = Field(default=True)

    def to_proxmox_args(self) -> dict:
        """Convertit vers les arguments Proxmox POST/PUT pour la config VM.

        Retourne un dict prêt pour `proxmox.vm.config(node, vmid, **args)`.
        """
        return {
            "cores": self.cores,
            "memory": self.memory,
            "ide2": f"{self.storage_device}:cloudinit",
            "citype": "nocloud",
            "ipconfig0": f"ip={self.wan_ip}/{self.wan_prefix},gw={self.wan_gateway}",
            "ipconfig1": f"ip={self.vxlan_gateway_ip}/24",
            "serial0": "socket",
            "vga": "serial0",
            "net0": f"virtio,bridge={self.wan_bridge}",
            "net1": f"virtio,bridge={self.vnet_bridge}",
            "onboot": 1 if self.onboot else 0,
            "tags": self.tags,
        }


class User(BaseModel):
    """Utilisateur Proxmox."""

    userid: str
    comment: str | None = None
    email: str | None = None
    realm: str | None = None
    enable: int | None = None


class Token(BaseModel):
    """Token API Proxmox."""

    tokenid: str
    comment: str | None = None
    expire: int | None = None
    privsep: int | None = None


class TokenCreateResponse(BaseModel):
    """Réponse à la création d'un token."""

    id: str = Field(..., alias="full-tokenid")
    value: str


class AclEntry(BaseModel):
    """Entrée ACL Proxmox."""

    path: str
    users: str | None = None
    tokens: str | None = None
    roles: list[str]
    propagate: int


class Pool(BaseModel):
    """Pool Proxmox."""

    poolid: str
    comment: str | None = None
    members: list[dict] | None = None


class PoolMember(BaseModel):
    """Membre d'un pool."""

    id: str
    type: str
    vmid: int | None = None


class SdnZone(BaseModel):
    """Zone SDN."""

    zone: str
    type: str
    comment: str | None = None


class Vnet(BaseModel):
    """Réseau virtuel (VNet) SDN."""

    vnet: str
    zone: str
    tag: int | None = None
    alias: str | None = None


class Subnet(BaseModel):
    """Subnet SDN."""

    subnet: str
    vnet: str
    type: str
    gateway: str | None = None


class VersionResponse(BaseModel):
    """Réponse à /version."""

    version: str
    release: str
    repoid: str
    console: str | None = None

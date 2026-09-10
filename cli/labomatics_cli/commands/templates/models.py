from pydantic import BaseModel, Field


class TempalteConfig(BaseModel):
    name: str
    vmid: int
    iso_url: str
    iso_filename: str
    memory: int
    cores: int = 2
    disk_size: str
    cpu_type: str = "kvm64"
    boot_timeout: int = 100
    cloudinit: bool = True
    ostype: str = "other"
    download_packages: bool = True
    extra_packages: list[str] = Field(default_factory=list)
    qcow_size: str | None = None
    uefi: bool = True

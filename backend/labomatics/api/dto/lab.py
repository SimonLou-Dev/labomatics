"""DTO pour le lab personnel (étudiant, professeur ou admin)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from labomatics.constants.enums import OwnerRole


class LabVmDTO(BaseModel):
    """VM du lab personnel."""

    id: str
    name: str
    cluster_name: str
    state: str
    cores: int
    memory: int
    disk: int
    created_at: datetime
    notes: str | None = None


class LabOwnerDTO(BaseModel):
    """Propriétaire du lab (étudiant, professeur ou admin).

    `cohort_name` n'a de sens que pour un étudiant (promo via enrollment) ;
    `None` pour un professeur/admin (#58).
    """

    id: str
    login: str
    first_name: str
    last_name: str
    email: str
    role: OwnerRole
    cohort_name: str | None = None
    created_at: datetime


class LabDataDTO(BaseModel):
    """Données complètes du lab personnel de son propriétaire."""

    owner: LabOwnerDTO
    vms: list[LabVmDTO] = Field(default_factory=list)
    wan_ip: str | None = None
    vxlan_tag: int | None = None
    openwrt_link: str | None = None
    proxmox_url: str | None = None

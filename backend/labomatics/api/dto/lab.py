"""DTO pour le lab personnel étudiant."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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


class StudentDTO(BaseModel):
    """Étudiant pour le contexte du lab."""

    id: str
    login: str
    first_name: str
    last_name: str
    email: str
    cohort_name: str
    created_at: datetime


class LabDataDTO(BaseModel):
    """Données complètes du lab personnel d'un étudiant."""

    student: StudentDTO
    vms: list[LabVmDTO] = Field(default_factory=list)
    wan_ip: str | None = None
    vxlan_tag: int | None = None
    openwrt_link: str | None = None

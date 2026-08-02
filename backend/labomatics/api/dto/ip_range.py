"""DTOs pour les plages d'IP WAN."""

from __future__ import annotations

from pydantic import BaseModel


class IpRangeDTO(BaseModel):
    """Plage d'IP WAN."""

    id: str
    name: str
    network: str
    gateway: str
    exclusions: list | None = None


class IpRangeCreateDTO(BaseModel):
    """Création d'une plage d'IP WAN."""

    name: str
    network: str
    gateway: str
    exclusions: list | None = None


class IpRangeUpdateDTO(BaseModel):
    """Mise à jour d'une plage d'IP WAN."""

    name: str | None = None
    network: str | None = None
    gateway: str | None = None
    exclusions: list | None = None


class IpAllocationDTO(BaseModel):
    """Allocation d'IP publique à un étudiant."""

    ip: str | None
    student_login: str | None
    student_first_name: str | None
    student_last_name: str | None
    wan_ip_taken_by: str | None
    is_taken: bool

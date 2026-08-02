"""DTOs pour les plages de VNI VXLAN."""

from __future__ import annotations

from pydantic import BaseModel


class VxlanRangeDTO(BaseModel):
    """Plage de VNI VXLAN."""

    id: str
    name: str
    vni_min: int
    vni_max: int
    base_network: str
    mtu: int
    exclusions: list | None = None


class VxlanRangeCreateDTO(BaseModel):
    """Création d'une plage de VNI VXLAN."""

    name: str
    vni_min: int
    vni_max: int
    base_network: str
    mtu: int = 1350
    exclusions: list | None = None


class VxlanRangeUpdateDTO(BaseModel):
    """Mise à jour d'une plage de VNI VXLAN."""

    name: str | None = None
    vni_min: int | None = None
    vni_max: int | None = None
    base_network: str | None = None
    mtu: int | None = None
    exclusions: list | None = None


class VxlanAllocationDTO(BaseModel):
    """Allocation de VNI VXLAN à un étudiant."""

    vni: int | None
    student_login: str | None
    student_first_name: str | None
    student_last_name: str | None
    vxlan_tag_taken_by: str | None
    is_taken: bool

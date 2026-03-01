#!/usr/bin/env python3
"""
Gestion des étudiants : chargement CSV et allocation réseau.

L'`id` du CSV est la clé stable de toutes les allocations :
  VMID, VNet tag, WAN IP, subnet VXLAN.
L'`index` (position triée) n'est utilisé que pour l'affichage.
"""

import csv
import ipaddress
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Student:
    id: int
    nom: str
    index: int = field(default=0, repr=False)  # position triée — affichage uniquement

    # ── identifiants Proxmox ──────────────────────────────────────────────

    def vmid(self, vmid_start: int) -> int:
        """VMID Proxmox = vmid_start + id.

        Stable : ne change pas si d'autres étudiants sont ajoutés/supprimés.
        """
        return vmid_start + self.id

    def vm_name(self) -> str:
        """Nom de la VM Proxmox."""
        return f"openwrt-{self.nom}"

    def vnet_name(self) -> str:
        """Nom du VNet SDN Proxmox — basé sur l'id (max 8 chars)."""
        return f"vn{self.id:05d}"

    # ── allocation réseau ─────────────────────────────────────────────────

    def wan_ip(self, wan_subnet: str) -> str:
        """IP WAN = adresse_réseau + id.

        Stable : id=1 → .1, id=42 → .42, indépendamment des autres étudiants.
        Lève ValueError si l'id dépasse la capacité du subnet.
        """
        net = ipaddress.IPv4Network(wan_subnet, strict=False)
        host = net.network_address + self.id
        if host >= net.broadcast_address:
            capacity = int(net.broadcast_address) - int(net.network_address) - 1
            raise ValueError(
                f"{self.nom} (id={self.id}) : WAN subnet {wan_subnet} "
                f"ne peut accueillir que {capacity} étudiants (id max = {capacity})"
            )
        return str(host)

    def vxlan_subnet(self, vxlan_pool: str) -> str:
        """Subnet VXLAN /24 — le Nième /24 du pool à partir de l'adresse de départ.

        vxlan_pool=10.100.0.0/12, id=1   → 10.100.1.0/24
        vxlan_pool=10.100.0.0/12, id=42  → 10.100.42.0/24
        vxlan_pool=10.100.0.0/12, id=256 → 10.101.0.0/24

        Lève ValueError si l'id dépasse les limites du pool.
        """
        pool_base = ipaddress.IPv4Address(vxlan_pool.split("/")[0])
        pool_prefix = int(vxlan_pool.split("/")[1])
        pool_net = ipaddress.IPv4Network(f"{pool_base}/{pool_prefix}", strict=False)

        subnet_start = pool_base + self.id * 256
        if subnet_start not in pool_net or subnet_start + 255 not in pool_net:
            raise ValueError(
                f"{self.nom} (id={self.id}) : VXLAN subnet {subnet_start}/24 "
                f"dépasse le pool {vxlan_pool}"
            )
        return f"{subnet_start}/24"

    def vxlan_ip(self, vxlan_pool: str) -> str:
        """IP de la VM dans son subnet VXLAN (.1)."""
        net = ipaddress.IPv4Network(self.vxlan_subnet(vxlan_pool))
        return str(net.network_address + 1)

    def vxlan_gateway(self, vxlan_pool: str) -> str:
        """Dernière IP hôte du subnet VXLAN (.254) — gateway."""
        net = ipaddress.IPv4Network(self.vxlan_subnet(vxlan_pool))
        return str(net.broadcast_address - 1)

    def pool_name(self) -> str:
        """Nom du pool Proxmox (= nom d'utilisateur)."""
        return self.nom

    def user_id(self) -> str:
        """Identifiant utilisateur Proxmox dans le realm local.

        Format : ``nom@pve``.
        Exemple : étudiant ``jdupont`` → ``"jdupont@pve"``.
        """
        return f"{self.nom}@pve"


def load_students(csv_path: Path) -> list[Student]:
    """Charge les étudiants depuis un CSV (colonnes: id, nom).

    Trie par id et assigne un index séquentiel pour l'affichage.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV étudiants introuvable : {csv_path}")

    students: list[Student] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(Student(id=int(row["id"]), nom=row["nom"].strip()))

    if not students:
        raise ValueError(f"CSV vide : {csv_path}")

    students.sort(key=lambda s: s.id)
    for i, student in enumerate(students, start=1):
        student.index = i  # ordre d'affichage uniquement

    return students

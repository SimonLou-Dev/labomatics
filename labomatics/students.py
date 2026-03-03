#!/usr/bin/env python3
"""
Gestion des étudiants : chargement CSV et identifiants Proxmox.

L'`id` du CSV est la clé stable de toutes les allocations :
  VMID = vmid_start + id
  VNet tag = id

L'allocation IP (WAN et VXLAN) est dynamique, réalisée depuis Proxmox
(voir :mod:`labomatics.ip_pool`). Il n'y a pas de calcul statique d'IP dans ce module.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Student:
    id: int
    nom: str
    prenom: str = ""
    flavor: str = ""
    index: int = field(default=0, repr=False)  # position triée — affichage uniquement

    # ── identifiants Proxmox ──────────────────────────────────────────────────

    def vmid(self, vmid_start: int) -> int:
        """VMID Proxmox = vmid_start + id (stable)."""
        return vmid_start + self.id

    def vm_name(self) -> str:
        """Nom de la VM OpenWrt dans Proxmox."""
        return f"openwrt-{self.nom}"

    def vnet_name(self) -> str:
        """Nom du VNet SDN Proxmox (max 8 chars, basé sur id)."""
        return f"vn{self.id:05d}"

    def vnet_alias(self) -> str:
        """Alias descriptif du VNet (prénom + nom) pour l'affichage Proxmox."""
        if self.prenom:
            return f"{self.prenom} {self.nom}"
        return self.nom

    def pool_name(self) -> str:
        """Nom du pool Proxmox (= login étudiant)."""
        return self.nom

    def user_id(self) -> str:
        """Identifiant utilisateur Proxmox (format nom@pve)."""
        return f"{self.nom}@pve"


def load_students(csv_path: Path) -> list[Student]:
    """Charge les étudiants depuis un CSV (colonnes: id, nom, prenom?, flavor?).

    Les colonnes `prenom` et `flavor` sont optionnelles (rétrocompatibilité).
    Trie par id et assigne un index séquentiel pour l'affichage.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV étudiants introuvable : {csv_path}")

    students: list[Student] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(Student(
                id=int(row["id"]),
                nom=row["nom"].strip(),
                prenom=row.get("prenom", "").strip(),
                flavor=row.get("flavor", "").strip(),
            ))

    if not students:
        raise ValueError(f"CSV vide : {csv_path}")

    students.sort(key=lambda s: s.id)
    for i, s in enumerate(students, start=1):
        s.index = i

    return students

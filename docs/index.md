# labomatics

CLI Python pour déployer automatiquement des environnements de lab réseau
sur un cluster Proxmox à partir d'un CSV d'étudiants.

```bash
pip install labomatics
labomatics init    # crée /etc/labomatics/
labomatics apply   # synchronise Proxmox avec le CSV
```

---

## Fonctionnalités

- **Déploiement piloté par CSV** — ajouter un étudiant dans `students.csv` suffit
- **Allocation IP dynamique** — WAN et VXLAN lus depuis Proxmox, sans fichier d'état local
- **Flavors** — profils de ressources (CPU/RAM/disk) assignés par étudiant
- **Quotas natifs Proxmox** — limits sur les pools, 403 à la surcharge
- **Daemon de quota** (`labomatics-quotad`) — stoppe la VM la plus gourmande si dépassement
- **Build de template** — pipeline Packer → provisioning SSH/guest-agent → conversion template
- **Isolation** — chaque étudiant est cantonné à son pool et son VNet VXLAN dédié

---

## Par où commencer ?

- **Administrateurs Proxmox** → [Installation et configuration](admin/setup.md)
- **Étudiants** → [Démarrage rapide OpenWrt](openwrt/base.md)

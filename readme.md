# labomatics

[![PyPI](https://img.shields.io/pypi/v/labomatics)](https://pypi.org/project/labomatics)
[![Python](https://img.shields.io/pypi/pyversions/labomatics)](https://pypi.org/project/labomatics)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](https://github.com/SimonLou-Dev/labomatrics/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://simonlou-dev.github.io/labomatrics/)

CLI Python pour déployer automatiquement des environnements de lab réseau
sur un cluster Proxmox à partir d'un CSV d'étudiants.

Pour chaque étudiant, labomatics provisionne : un pool Proxmox, un VNet VXLAN,
une VM OpenWrt (routeur), un compte utilisateur avec ACL, et un jeu de credentials.

```
pip install labomatics
labomatics init       # crée /etc/labomatics/ avec les configs par défaut
labomatics apply      # synchronise Proxmox avec le CSV
```

---

## Fonctionnalités

- **Déploiement piloté par CSV** — ajouter un étudiant dans `students.csv` suffit
- **Allocation IP dynamique** — WAN et VXLAN lus depuis Proxmox, sans fichier d'état local
- **Flavors** — profils de ressources (CPU/RAM/disk) assignés par étudiant
- **Quotas natifs Proxmox** — limits sur les pools (`max_cpu/ram/disk`), 403 à la surcharge
- **Daemon de quota** (`labomatics-quotad`) — surveille et stoppe la VM la plus gourmande si dépassement
- **Build de template** — pipeline Packer → provisioning SSH/guest-agent → conversion template
- **Isolation** — chaque étudiant est cantonné à son pool et son VNet VXLAN dédié

---

## Installation

```bash
pip install labomatics
```

Ou depuis les sources :

```bash
git clone https://github.com/SimonLou-Dev/labomatrics
cd labomatics-cli
pip install -e ".[dev]"
```

---

## Démarrage rapide

### 1. Prérequis Proxmox

- Proxmox VE 8+ avec SDN activé
- Zone VXLAN SDN créée (ex. `esgilab`)
- Stockage partagé entre tous les nœuds (Ceph / NFS / ZFS répliqué)
- Token API Proxmox avec les droits nécessaires (Administrator sur /)
- Template OpenWrt sur le stockage partagé

### 2. Initialisation

```bash
sudo labomatics init
# Crée /etc/labomatics/{infra.yaml, .env, students.csv}
```

### 3. Configuration

```bash
# /etc/labomatics/.env
PROXMOX_HOST=192.168.1.100
PROXMOX_TOKEN_ID=root@pam!labomatics
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

```yaml
# /etc/labomatics/infra.yaml
version: "v1"
openwrt:
  vmid_start: 10000
  template_vmid: 90200
  storage: zfs-store
  wan_bridge: vmbr0
  network:
    zone_name: esgilab
    wan_pool:
      network: 172.16.0.0/24
      gateway: 172.16.0.254
      exclude: ["172.16.0.1-172.16.0.10"]
    vxlan_pool:
      network: 10.100.0.0/12
      exclude: []
flavors:
  CO1: {cpu: 4, ram: 8192, disk: 40}
  CO2: {cpu: 8, ram: 16384, disk: 80}
```

### 4. Étudiants

```csv
# /etc/labomatics/students.csv
id,nom,prenom,flavor
18,jdupont,Jean,CO1
240,mkorniev,Mikhail,CO2
```

L'`id` est stable et sert de clé pour le VMID et le tag VXLAN. Ne jamais le réutiliser.

### 5. Déployer

```bash
labomatics diff     # aperçu sans modification
labomatics apply    # déploiement avec confirmation
```

---

## Commandes CLI

| Commande | Description |
|---|---|
| `apply [--yes]` | Synchronise Proxmox avec le CSV |
| `diff` | Aperçu des changements (lecture seule) |
| `pools` | Liste les pools gérés |
| `zones` | Liste les zones SDN |
| `vnets [--zone]` | Liste les VNets SDN |
| `vms [--pool]` | Liste les VMs des pools gérés |
| `find <query>` | Recherche par IP WAN, VNet ou nom |
| `credentials` | Affiche les credentials générés |
| `ips` | État des pools IP avec % d'utilisation |
| `status` | Ressources CPU/RAM/disk par étudiant vs flavor |
| `recreate <nom> [--yes]` | Recrée la VM OpenWrt d'un étudiant |
| `build-template [nom]` | Build template via Packer + provisioning |
| `init [--dir]` | Initialise la configuration |

---

## Daemon de quota

`labomatics-quotad` surveille les ressources des pools étudiants et arrête
automatiquement la VM la plus gourmande en RAM si un quota est dépassé.
La VM OpenWrt n'est jamais arrêtée.

```bash
# Installation systemd
cp systemd/labomatics-quotad.service /etc/systemd/system/
systemctl enable --now labomatics-quotad
```

---

## Build de template

```bash
# Construire toutes les templates définies dans infra.yaml
labomatics build-template

# Construire une template spécifique
labomatics build-template ubuntu-24.04
```

Pipeline : suppression de l'existante → Packer build → provisioning SSH/guest-agent
→ shutdown → suppression NICs → conversion template Proxmox.

---

## Structure du projet

```
labomatics-cli/
├── labomatics/               # Package Python
│   ├── commands/             # Sous-commandes CLI
│   ├── proxmox/              # Couche API Proxmox
│   ├── daemon/               # labomatics-quotad
│   └── templates/            # Fichiers de config exemple
├── docs/
│   ├── admin/                # Documentation administrateur
│   └── openwrt/              # Documentation utilisateur final
├── scripts/
│   └── build-openwrt-vm-template.sh
├── systemd/
│   └── labomatics-quotad.service
├── infra.yaml                # Config de l'infra (exemple)
├── students.csv              # CSV étudiants (exemple)
└── pyproject.toml
```

---

## Documentation

- **[Admin](https://simonlou-dev.github.io/labomatrics/admin/overview/)** — installation, configuration, CLI (administrateurs Proxmox)
- **[Utilisateur OpenWrt](https://simonlou-dev.github.io/labomatrics/openwrt/base/)** — réseau, DHCP, NAT, firewall (étudiants)

---

## Licence

MIT — voir [LICENSE](https://github.com/SimonLou-Dev/labomatrics/blob/main/LICENSE).

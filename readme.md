# proxmox-lab — esgilabs

Outil CLI Python pour déployer automatiquement un environnement de lab réseau
sur un cluster Proxmox à partir d'un CSV d'étudiants.

Pour chaque étudiant, le script provisionne : un pool Proxmox, un VNet VXLAN,
une VM OpenWrt (routeur), un compte utilisateur et des ACL d'accès.

### Isolation par tenant

Chaque étudiant est isolé dans son propre **pool Proxmox** qui délimite son périmètre
de ressources : il ne voit et ne peut opérer que les VMs/LXC qui lui appartiennent.
Son réseau interne est un VNet VXLAN dédié, sans communication possible vers les
tenants voisins.

### Pool de templates partagé

Un pool `template` global (configurable) regroupe les templates accessibles en
lecture à tous les étudiants. Ils peuvent cloner ces templates dans leur propre pool
pour démarrer leurs VMs.

Les templates peuvent être construites avec **Packer** —
cf. [cours_m1_ansible](https://github.com/SimonLou-Dev/cours_m1_ansible) pour des
exemples de pipelines Packer/Ansible ciblant Proxmox.

> **Contrainte importante** : avant de convertir une VM en template, supprimer son
> interface réseau (ou la déconnecter du VNet) — sinon le clone héritera d'une
> configuration réseau figée et ne pourra pas être recloné à cause des permissions de l'utilisateur

---

## Structure du projet

```
proxmox-lab/
├── esgilabs/               # Package Python (CLI + logique)
│   ├── __main__.py         # Entrée CLI : python -m esgilabs
│   ├── commands/           # Implémentation des sous-commandes
│   │   ├── apply.py        # apply, diff
│   │   ├── inspect.py      # pools, zones, vnets, vms
│   │   ├── find.py         # find
│   │   └── creds.py        # credentials
│   ├── proxmox/            # Couche API Proxmox
│   │   ├── acl.py          # Utilisateurs + ACL
│   │   ├── pools.py        # Pools de ressources
│   │   ├── sdn.py          # Zones + VNets SDN
│   │   ├── vms.py          # VMs + sélection de nœud
│   │   ├── tasks.py        # Attente de tâches asynchrones
│   │   └── client.py       # Connexion API
│   ├── config.py           # Configuration (Pydantic)
│   ├── students.py         # Gestion des étudiants (CSV + allocations réseau)
│   ├── diff.py             # Calcul CSV ↔ Proxmox
│   ├── credentials.py      # credentials.csv
│   └── deploy.py           # Clone/suppression VM + LXC
├── scripts/
│   └── build-openwrt-vm-template.sh  # Build de la template OpenWrt
├── docs/
│   ├── admin/              # Documentation administrateur
│   │   ├── overview.md     # Architecture + flux d'exécution
│   │   ├── setup.md        # Installation, config, ordre de mise en place
│   │   ├── cli.md          # Référence des commandes
│   │   └── template.md     # Build de la template OpenWrt
│   └── openwrt/            # Documentation utilisateur final
│       ├── base.md         # Accès, réseau, credentials
│       ├── proxmox.md      # Interface Proxmox, pool, templates
│       ├── dhcp.md
│       ├── nat.md
│       ├── dns.md
│       └── firewall.md
├── infra.yaml              # Configuration de l'infrastructure
├── students.csv            # Liste des étudiants (id, nom)
├── .env                    # Credentials Proxmox (non versionné)
└── requirements.txt
```

---

## Démarrage rapide

### 1. Prérequis

- Python 3.11+
- Cluster Proxmox avec SDN activé
- Zone VXLAN SDN créée (`esgilab` par défaut)
- Au moins une template VM sur un stockage partagé (Ceph / NFS / ZFS répliqué)

### 2. Installation

```bash
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Renseigner PROXMOX_HOST, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET
```

Éditer `infra.yaml` selon votre infrastructure :

```yaml
openwrt:
  vmid_start: 10000
  template_vmid: 90200
  storage: zfs-store          # Stockage partagé entre tous les nœuds
  students_csv: students.csv
  template_pool: template     # Pool contenant les templates du lab
  network:
    zone_name: esgilab
    wan_subnet: 172.16.0.0/24
    wan_gateway: 172.16.0.254
    vxlan_pool: 10.100.0.0/12
```

### 4. Préparer les templates

Placez vos templates sur le stockage partagé et ajoutez-les au pool `template` :

```bash
pvesh set /pools/template -vms <vmid>
```

> Le script `scripts/build-openwrt-vm-template.sh` permet de construire une template
> OpenWrt (routeur). Pour les autres VMs du lab, utilisez Packer —
> cf. [cours_m1_ansible](https://github.com/SimonLou-Dev/cours_m1_ansible).
>
> **Important** : retirer l'interface réseau d'une VM avant de la convertir en
> template, sinon le clonage sera impossible pour l'utilisateur

### 5. Peupler le CSV étudiant

```csv
# students.csv
id,nom
18,jdupont
240,mkorniev
```

### 6. Déployer

```bash
python -m esgilabs diff    # Aperçu sans modification
python -m esgilabs apply   # Déploiement avec confirmation
```

---

## Commandes CLI

| Commande                        | Description                                      |
|---------------------------------|--------------------------------------------------|
| `apply [--yes]`                 | Synchronise Proxmox avec le CSV                  |
| `diff`                          | Affiche le diff sans rien modifier               |
| `pools`                         | Liste les pools gérés                            |
| `zones`                         | Liste les zones SDN                              |
| `vnets [--zone ZONE]`           | Liste les VNets SDN                              |
| `vms [--pool POOL]`             | Liste les VMs des pools gérés                    |
| `find <IP\|VNet\|nom>`          | Recherche un étudiant                            |
| `credentials`                   | Affiche les credentials générés                  |

Voir [docs/admin/cli.md](docs/admin/cli.md) pour la référence complète.

---

## Allocations réseau

Toutes les allocations sont basées sur l'`id` CSV de l'étudiant (stable) :

| Ressource       | Formule                              | Exemple (id=18)       |
|-----------------|--------------------------------------|-----------------------|
| VMID            | `vmid_start + id`                    | `10018`               |
| IP WAN          | `wan_subnet + id`                    | `172.16.0.18`         |
| Subnet VXLAN    | `vxlan_pool + id × 256` → `/24`     | `10.100.18.0/24`      |
| VNet            | `vn{id:05d}`                         | `vn00018`             |
| User Proxmox    | `nom@pve`                            | `jdupont@pve`         |

---

## Documentation

- **[docs/admin/](docs/admin/)** — pour les administrateurs Proxmox
- **[docs/openwrt/](docs/openwrt/)** — pour les étudiants (utilisateurs finaux)

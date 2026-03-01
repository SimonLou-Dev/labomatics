# Installation et configuration

> **Audience** : administrateur du lab Proxmox.

---

## Prérequis cluster Proxmox

Avant de lancer le script, le cluster Proxmox doit être configuré :

### 1. Zone SDN VXLAN

Une zone SDN de type VXLAN doit exister (ex. `esgilab`). Le script **ne la crée pas** —
elle doit être créée manuellement dans `Datacenter → SDN → Zones`.

```
Type       : VXLAN
Zone ID    : esgilab
Peers      : IPs de tous les nœuds du cluster
```

### 2. Pool template

Un pool Proxmox nommé `template` (ou le nom défini dans `template_pool`) doit exister
et contenir la template OpenWrt. Le script **ne crée pas ce pool** — il est créé
manuellement et la template y est ajoutée après le build.

```
Datacenter → Pools → Create → Pool ID: template
```

### 3. Stockage partagé

La template OpenWrt doit résider sur un **stockage accessible depuis tous les nœuds**
(Ceph RBD, NFS, ZFS over iSCSI…). Le déploiement sélectionne le nœud le moins chargé
dynamiquement — un stockage local (non partagé) empêcherait le clone depuis d'autres nœuds.

Voir [template.md](template.md) pour la création de la template.

### 4. Token API Proxmox

Créer un token API avec les permissions nécessaires :

```
Datacenter → Permissions → API Tokens → Add
User        : root@pam  (ou un compte dédié)
Token ID    : esgilabs
Privilege Separation : non (pour hériter des droits root)
```

Permissions minimales requises sur `/` (ou par chemin) :

| Permission                | Explication                                        |
|---------------------------|----------------------------------------------------|
| `Sys.Modify`              | Création/suppression de zones SDN, apply SDN       |
| `Pool.Allocate`           | Création/suppression de pools                      |
| `VM.Allocate`             | Clone de template, suppression de VMs              |
| `VM.Config.*`             | Configuration cloud-init                           |
| `User.Modify`             | Création/suppression d'utilisateurs et ACL         |
| `Datastore.AllocateSpace` | Allocation d'espace sur le stockage                |

---

## Installation Python

```bash
# Python 3.11+ requis
pip install -r requirements.txt
```

**`requirements.txt`** :
```
proxmoxer
requests
pydantic
pydantic-settings
python-dotenv
rich
pyyaml
```

---

## Configuration

### `.env` — Credentials Proxmox

```bash
cp .env.example .env
# Éditer .env
```

```ini
PROXMOX_HOST=192.168.1.10          # IP ou FQDN du cluster Proxmox
PROXMOX_TOKEN_ID=root@pam!esgilabs # format : user@realm!token-name
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> Ne pas versionner `.env` — il contient le secret du token API.

### `infra.yaml` — Configuration de l'infrastructure

| Clé                        | Exemple             | Description                                              |
|----------------------------|---------------------|----------------------------------------------------------|
| `openwrt.vmid_start`       | `10000`             | Premier VMID alloué (VMID = vmid_start + student.id)    |
| `openwrt.template_vmid`    | `90200`             | VMID de la template OpenWrt (créée par le script build)  |
| `openwrt.storage`          | `zfs-store`         | Stockage partagé entre tous les nœuds                    |
| `openwrt.students_csv`     | `students.csv`      | Chemin vers le CSV étudiants (relatif à la racine)       |
| `openwrt.template_pool`    | `template`          | Pool Proxmox contenant les templates globales            |
| `openwrt.network.zone_name`| `esgilab`           | Nom de la zone SDN VXLAN (doit exister avant apply)      |
| `openwrt.network.wan_subnet` | `172.16.0.0/24`  | Subnet WAN — IP étudiant = réseau + id                   |
| `openwrt.network.wan_gateway`| `172.16.0.254`   | Passerelle WAN                                           |
| `openwrt.network.vxlan_pool` | `10.100.0.0/12`  | Pool VXLAN — subnet étudiant = pool_base + id×256 → /24  |

### `students.csv` — Liste des étudiants

```csv
id,nom
18,jdupont
240,mkorniev
42,asmith
```

- `id` : entier unique et stable (clé de toutes les allocations réseau)
- `nom` : identifiant alphanumérique (devient le nom de pool et `nom@pve`)

> **Important** : ne jamais réutiliser un `id` après suppression d'un étudiant —
> cela réattribuerait son subnet VXLAN et son IP WAN à quelqu'un d'autre.

---

## Ordre de mise en place (à suivre dans cet ordre)

> **Ces étapes sont à réaliser une seule fois avant le premier `apply`.**

### Étape 1 — Build de la template OpenWrt

La template OpenWrt doit être créée avant tout déploiement. Voir [template.md](template.md)
pour le détail complet.

```bash
# Sur n'importe quel nœud Proxmox ayant accès au stockage partagé, en root
bash scripts/build-openwrt-vm-template.sh 23.05.5 90200 zfs-store openwrt

# Ajouter la template au pool template (pour les ACL étudiants)
pvesh set /pools/template -vms 90200
```

### Étape 2 — Zone SDN VXLAN

Créer la zone SDN dans `Datacenter → SDN → Zones` (si elle n'existe pas) :

```
Type    : VXLAN
Zone ID : esgilab
Peers   : IPs de tous les nœuds du cluster
```

### Étape 3 — Pool template

Créer le pool template dans `Datacenter → Pools → Create` (si non existant) :

```
Pool ID : template
```

### Étape 4 — Premier `apply`

```bash
# Vérifier le diff avant d'appliquer
python -m esgilabs diff

# Appliquer (avec confirmation interactive)
python -m esgilabs apply

# Appliquer sans confirmation (CI/CD)
python -m esgilabs apply --yes
```

Après `apply`, le fichier `credentials.csv` est généré dans le même répertoire
que `students.csv`. Il contient les mots de passe Proxmox générés. **Ne pas le
versionner.**

```csv
nom,userid,password,wan_ip
jdupont,jdupont@pve,Abc123XyzDef,172.16.0.18
mkorniev,mkorniev@pve,DefGhi456Jkl,172.16.0.240
```

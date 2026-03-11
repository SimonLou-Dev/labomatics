# Build de la template OpenWrt

> **Audience** : administrateur Proxmox — opération à réaliser **une seule fois**
> avant le premier déploiement.

La commande `labomatics build-openwrt` télécharge la dernière image OpenWrt officielle,
l'enrichit hors-ligne (mot de passe, SSH, NAT, HTTPS, cloud-init NoCloud)
et l'enregistre comme template Proxmox. Toutes les VMs déployées par labomatics en sont
des clones complets.

---

## Stockage partagé — prérequis impératif

> **La template doit impérativement résider sur un stockage partagé entre tous
> les nœuds du cluster** (Ceph RBD, NFS, ZFS over iSCSI…).

labomatics sélectionne dynamiquement le nœud de déploiement (celui avec le plus
de mémoire libre). Si le stockage est local, le clone sera effectué sur le nœud
source — ce qui concentre les déploiements sur un seul nœud.

Après la création de la template, vérifier qu'elle est visible depuis tous les nœuds
via le stockage partagé.

---

## Exécution

```bash
# En root sur un nœud Proxmox (vmid et storage lus depuis infra.yaml)
labomatics build-openwrt

# Paramètres explicites
labomatics build-openwrt --version 24.10.0 --vmid 90200 --storage zfs-store --password openwrt
```

### Paramètres

| Option       | Défaut                         | Description                                              |
|--------------|--------------------------------|----------------------------------------------------------|
| `--version`  | Dernière stable (auto-détecté) | Version OpenWrt à télécharger depuis downloads.openwrt.org |
| `--vmid`     | `infra.yaml → template_vmid`   | VMID Proxmox (doit correspondre à `template_vmid` dans `infra.yaml`) |
| `--storage`  | `infra.yaml → storage`         | Stockage partagé cible                                   |
| `--password` | `openwrt`                      | Mot de passe root injecté dans l'image                   |

> Si la VM `vmid` existe déjà, la commande demande confirmation avant de la détruire.

La commande ajoute automatiquement la template au pool `template` (créé si absent).

---

## Ce que la commande fait

### 1. Téléchargement de l'image

Dernière version stable détectée automatiquement depuis `downloads.openwrt.org/releases/`.
Image `x86-64-generic-ext4-combined` téléchargée via `wget`.
Le format `ext4-combined` contient deux partitions : boot (p1) et root (p2).
Seule **p2** est montée via loop device — l'image n'est jamais démarrée.

### 2. Mot de passe root

Hash généré avec `openssl passwd -1` (MD5-crypt) et injecté dans `/etc/shadow`
(fallback `/etc/passwd`). Tout se fait hors-ligne par montage de partition.

### 3. SSH (Dropbear)

Dropbear configuré sur le port 22 avec activation automatique au boot :

```
/etc/dropbear/dropbear.conf   ← DROPBEAR_EXTRA_ARGS="-p 22"
/etc/rc.d/S50dropbear         ← symlink vers /etc/init.d/dropbear
```

### 4. Certificat HTTPS auto-signé

Certificat RSA 2048 bits, valable 10 ans, généré et stocké dans l'image :

```
/etc/uhttpd.crt   ← certificat public
/etc/uhttpd.key   ← clé privée (chmod 600)
```

Utilisé par uhttpd (LuCI) pour servir HTTPS dès le premier boot.

### 5. Script uci-defaults `99-proxmox-init`

Injecté dans `/etc/uci-defaults/` — s'exécute **automatiquement au premier boot**
puis se supprime. Copie permanente conservée dans `/etc/proxmox-init.sh`.

Il effectue au premier boot :

1. **Lecture du drive cloud-init NoCloud** (`/dev/sr0`, injecté par Proxmox via `ide2`)
   - `user-data` → hostname
   - `network-config` → interfaces réseau (format Proxmox v1)
   - Interface avec gateway → `network.wan` / sans gateway → `network.lan`

2. **Configuration uhttpd** : écoute sur `0.0.0.0:80` et `0.0.0.0:443`,
   utilise le certificat de l'étape 4, redirige HTTP → HTTPS.

3. **NAT (masquerade)** : activé sur la zone WAN — les VMs du réseau LAN/VXLAN
   peuvent accéder à Internet via le routeur OpenWrt.

4. **Règles firewall** :
   - HTTP/HTTPS (80, 443) autorisés depuis la zone WAN
   - SSH (22) autorisé depuis la zone WAN

5. **SSH depuis WAN** : Dropbear configuré pour écouter sur toutes les interfaces
   (y compris WAN) — accès SSH direct depuis le réseau du lab.

### 6. Création du template Proxmox

```bash
qm create <vmid> --memory 256 --cores 1 --net0 virtio,bridge=vmbr0 \
  --serial0 socket --vga serial0 --ostype l26

qm importdisk <vmid> openwrt.img <storage>
# Le disk ID réel est lu depuis qm config (compatible tous types de stockage)
qm set <vmid> --virtio0 <disk_id>,discard=on,iothread=1 --boot order=virtio0
qm template <vmid>

# Ajout automatique au pool template
pvesh set /pools/template -vms <vmid>
```

---

## Correspondance avec `infra.yaml`

```yaml
openwrt:
  template_vmid: 90200   # doit correspondre au vmid du build
  storage: zfs-store     # même stockage partagé utilisé pour le build
  template_pool: template  # pool auquel ajouter la template
```

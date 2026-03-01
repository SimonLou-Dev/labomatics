# Build de la template OpenWrt

> **Audience** : administrateur Proxmox — opération à réaliser **une seule fois**
> avant le premier déploiement.

Le script `scripts/build-openwrt-vm-template.sh` télécharge une image OpenWrt officielle,
l'enrichit hors-ligne (mot de passe, SSH, HTTPS, qemu-guest-agent, cloud-init NoCloud)
et l'enregistre comme template Proxmox. Toutes les VMs déployées par `esgilabs` en sont
des clones complets.

---

## Stockage partagé — prérequis impératif

> **La template doit impérativement résider sur un stockage partagé entre tous
> les nœuds du cluster** (Ceph RBD, NFS, ZFS over iSCSI…).

`esgilabs` sélectionne dynamiquement le nœud de déploiement (celui avec le plus
de mémoire libre). Un clone depuis un stockage local n'est possible que depuis
le nœud hébergeant la template — ce qui bloquerait les déploiements sur les autres
nœuds.

Après la création de la template sur un nœud, vérifier qu'elle est visible depuis
tous les nœuds via le stockage partagé.

---

## Exécution

```bash
# Sur n'importe quel nœud Proxmox ayant accès au stockage partagé, en root
bash scripts/build-openwrt-vm-template.sh [version] [vmid] [storage] [root_password]
```

### Paramètres

| Paramètre       | Défaut      | Description                                         |
|-----------------|-------------|-----------------------------------------------------|
| `version`       | `23.05.5`   | Version OpenWrt à télécharger                       |
| `vmid`          | `90200`     | VMID Proxmox du template (doit correspondre à `template_vmid` dans `infra.yaml`) |
| `storage`       | `local-lvm` | Pool de stockage partagé (ex. `zfs-store`, `ceph`)  |
| `root_password` | `openwrt`   | Mot de passe root injecté dans l'image              |

```bash
# Exemple du lab
bash scripts/build-openwrt-vm-template.sh 23.05.5 90200 zfs-store openwrt
```

> Si la VM `vmid` existe déjà, le script demande confirmation avant de la détruire.

### Ajouter la template au pool template

Une fois la VM convertie en template, l'ajouter au pool `template` (pool global
du lab) pour que les étudiants puissent la voir depuis leur interface Proxmox :

```bash
# Via pvesh sur le nœud
pvesh set /pools/template -vms 90200
```

Ou via l'interface web : `Datacenter → Pools → template → Add → VM 90200`.

---

## Ce que le script fait

### 1. Téléchargement de l'image

Image `x86-64-generic-ext4-combined` téléchargée depuis `downloads.openwrt.org`.
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

### 5. qemu-guest-agent

Paquet `qemu-ga` récupéré depuis les dépôts officiels OpenWrt, extrait et copié
dans l'image. Symlink rc.d créé pour l'activation au boot.

Permet à Proxmox de : récupérer les IPs de la VM, exécuter des commandes guest,
effectuer un shutdown propre depuis l'interface.

### 6. Script uci-defaults `99-proxmox-init`

Injecté dans `/etc/uci-defaults/` — s'exécute **automatiquement au premier boot**
puis se supprime. Copie permanente conservée dans `/etc/proxmox-init.sh`.

Il effectue au premier boot :

1. **Lecture du drive cloud-init NoCloud** (`/dev/sr0`, injecté par Proxmox via `ide2`)
   - `user-data` → hostname
   - `network-config` → interfaces réseau (format Proxmox v1)
   - Interface avec gateway → `network.wan` / sans gateway → `network.lan`

2. **Configuration uhttpd** : écoute sur `0.0.0.0:80` et `0.0.0.0:443`,
   utilise le certificat de l'étape 4, redirige HTTP → HTTPS.

3. **Règle firewall** : autorise HTTP/HTTPS entrant depuis la zone WAN
   (bloqué par défaut sur OpenWrt).

### 7. Création du template Proxmox

```bash
qm create <vmid> \
  --memory 256 \
  --cores 1 \
  --net0 virtio,bridge=vmbr0 \
  --serial0 socket \
  --vga serial0 \
  --ostype l26

qm importdisk <vmid> openwrt.img <storage>
qm set <vmid> --virtio0 <storage>:vm-<vmid>-disk-0,discard=on,iothread=1
qm template <vmid>
```

---

## Correspondance avec `infra.yaml`

```yaml
openwrt:
  template_vmid: 90200   # doit correspondre au vmid du build
  storage: zfs-store     # même stockage partagé utilisé pour le build
  template_pool: template  # pool auquel ajouter la template
```

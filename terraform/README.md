# Infrastructure de Test Proxmox avec Terraform + libvirt

Configuration Terraform pour provisioner 3 nœuds Proxmox dans libvirt/QEMU pour tester labomatics.

## Architecture

- **Réseau**: NAT (192.168.122.0/24)
- **VMs**: 3 nœuds Proxmox
  - `pxmx1`: 4 vCPU, 4 GB RAM, 50 GB + 100 GB disques
  - `pxmx2`: 4 vCPU, 4 GB RAM, 50 GB disque
  - `pxmx3`: 4 vCPU, 4 GB RAM, 50 GB disque
- **ISO**: Proxmox VE 9.1 en CDROM

## Prérequis

1. **KVM/libvirt installé**:
   ```bash
   sudo dnf install libvirt libvirt-daemon qemu-kvm virt-manager
   sudo usermod -a -G libvirt $USER
   newgrp libvirt
   ```

2. **Terraform >= 1.0**:
   ```bash
   terraform version
   ```

3. **Provider libvirt** (sera téléchargé automatiquement)

## Déploiement

### 1. Initialiser Terraform
```bash
cd terraform/libvirt-proxmox
terraform init
```

### 2. Valider la config
```bash
terraform validate
terraform plan
```

### 3. Créer les ressources
```bash
terraform apply
```

La création des VMs prend quelques minutes (création des volumes).

### 4. Surveiller le déploiement
```bash
# Lister les VMs
virsh list

# Accéder à la console d'une VM
virsh console pxmx1
virsh console pxmx2
virsh console pxmx3

# Obtenir les adresses IP (après boot)
virsh net-dhcp-leases proxmox-lab-net
```

## Installation Proxmox

Une fois les VMs démarrées:

1. **Accéder à la console**: `virsh console pxmx1`
2. **Installer Proxmox**: Suivre l'installateur standard
   - Hostname: `pxmx1.proxmox.lab` (ou pxmx2, pxmx3)
   - Network: DHCP (auto détecté)
   - Storage: `/dev/vda` (boot) et `/dev/vdb` (si pxmx1)
3. **Après installation**: Redémarrer (Ctrl+D) et accéder à `https://192.168.122.XXX:8006`

## Variables personnalisables

Voir `variables.tf`:

```hcl
vm_memory           = 4096  # MB
vm_vcpu             = 4
boot_disk_size_gb   = 50
extra_disk_size_gb  = 100  # Seulement pour pxmx1
network_subnet      = "192.168.122.0/24"
iso_path            = "/home/virtu/iso/proxmox-ve_9.1-1.iso"
```

Modifier via `-var` ou fichier `.tfvars`:
```bash
terraform apply -var="vm_memory=8192"
```

## Nettoyage

```bash
terraform destroy
```

Cela supprime:
- ✓ Les 3 VMs
- ✓ Les 4 volumes disque
- ✓ Le réseau NAT
- ✓ Le storage pool

**Note**: L'ISO n'est pas supprimée (référence source externe).

## Dépannage

### Les VMs ne démarrent pas
```bash
# Vérifier les erreurs
virsh dominfo pxmx1
virsh domstats pxmx1

# Relancer une VM
virsh start pxmx1
```

### DHCP non fonctionnel
```bash
# Vérifier le réseau
virsh net-info proxmox-lab-net
virsh net-dhcp-leases proxmox-lab-net

# Redémarrer le réseau
virsh net-destroy proxmox-lab-net
virsh net-start proxmox-lab-net
```

### Disque plein
```bash
# Vérifier l'usage
du -sh /tmp/libvirt-pool/

# Agrandir les disques dans Terraform et refaire apply
```

## Stockage partagé NFS (pxmx1)

### Configuration du disque supplémentaire (100 GB)

Sur **pxmx1**, après l'installation Proxmox:

```bash
# 1. Identifier les disques
lsblk
# Vous verrez: vda (50GB, root) et vdb (100GB, données)

# 2. Formatter le disque
mkfs.ext4 /dev/vdb

# 3. Monter le disque
mkdir -p /data
mount /dev/vdb /data

# 4. Rendre persistant (ajouter à /etc/fstab)
echo "/dev/vdb /data ext4 defaults,nofail 0 2" >> /etc/fstab
```

### Configuration du serveur NFS (pxmx1)

```bash
# 1. Installer nfs-server
apt update
apt install nfs-kernel-server

# 2. Configurer /etc/exports
tee -a /etc/exports << 'EOF'
/data 172.29.20.0/24(rw,sync,no_subtree_check,no_root_squash)
EOF

# 3. Appliquer la config
exportfs -a
systemctl restart nfs-kernel-server

# 4. Vérifier les exports
showmount -e localhost
```

### Montage NFS via l'UI Proxmox

Dans chaque nœud Proxmox (**pxmx2**, **pxmx3**, etc.):

1. **Datacenters** → **Storage** → **Add** → **NFS**
2. Remplir:
   - **ID**: `nfs-data` (ou autre nom)
   - **Server**: `172.29.20.X` (IP de pxmx1 sur le LAN)
   - **Export**: `/data`
   - **Content**: Cocher les types de contenu (Images, Backups, etc.)
3. **Add** et valider

## Partage du projet avec les VMs (virtiofs)

### Sur l'hôte

1. **Démarrer virtiofsd** pour partager le répertoire:

```bash
# Installer virtiofsd (si pas déjà présent)
apt install virtiofsd

# Créer un socket pour virtiofsd
mkdir -p /tmp/virtiofs
cd /tmp/virtiofs

# Démarrer virtiofsd en arrière-plan
virtiofsd --socket-path=workspace.sock --shared-dir=/home/slou/Dev/cours/proxmox-lab &
```

2. **Éditer chaque VM pour ajouter virtiofs**:

```bash
virsh edit pxmx1
```

Ajouter dans la section `<devices>`:
```xml
<filesystem type="virtiofs">
  <source dir="/tmp/virtiofs/workspace.sock"/>
  <target dir="workspace"/>
</filesystem>
```

3. **Relancer les VMs**:
```bash
virsh destroy pxmx1
virsh start pxmx1
```

### Dans chaque VM (pxmx1, pxmx2, pxmx3)

```bash
# 1. Créer le point de montage
mkdir -p /workspace

# 2. Monter le filesystem virtiofs
mount -t virtiofs workspace /workspace

# 3. Vérifier le montage
ls -la /workspace

# 4. Rendre persistant (ajouter à /etc/fstab)
echo "workspace /workspace virtiofs defaults 0 0" >> /etc/fstab
```

## Architecture stockage finale

```
Hôte (KVM)
├── /home/slou/Dev/cours/proxmox-lab
│   └── virtiofsd (workspace.sock) --> /workspace (virtiofs) à chaque VM
└── VMs (172.29.20.0/24)
    ├── pxmx1
    │   ├── /dev/vda (50 GB, Proxmox)
    │   ├── /dev/vdb (100 GB, ext4)
    │   │   └── /data --> NFS export
    │   └── /workspace --> virtiofs depuis l'hôte
    │
    ├── pxmx2
    │   ├── /dev/vda (50 GB, Proxmox)
    │   ├── /mnt/data --> NFS depuis pxmx1 (via UI Proxmox)
    │   └── /workspace --> virtiofs depuis l'hôte
    │
    └── pxmx3
        ├── /dev/vda (50 GB, Proxmox)
        ├── /mnt/data --> NFS depuis pxmx1 (via UI Proxmox)
        └── /workspace --> virtiofs depuis l'hôte
```

## Pour tester avec labomatics

Une fois les 3 nœuds Proxmox installés, NFS configuré, virtiofsd lancé, et `/workspace` monté:

1. **Récupérer les IPs LAN** via l'UI Proxmox ou `virsh`:
   ```bash
   virsh net-dhcp-leases proxmox-lab-internal
   ```

2. **Créer `/etc/labomatics/infra.yaml`** pointant vers les nœuds

3. **Lancer les commandes labomatics depuis `/workspace`**:
   ```bash
   cd /workspace
   labomatics apply
   labomatics status
   ```

4. **Fichiers synchronisés en temps réel**:
   - Éditer sur l'hôte: `/home/slou/Dev/cours/proxmox-lab`
   - Visible instantanément dans les VMs: `/workspace` (virtiofs)
   - Aucune latence, parfait pour dev/test

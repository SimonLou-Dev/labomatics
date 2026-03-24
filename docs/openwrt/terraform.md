# Terraform avec le provider bpg/proxmox

> **Audience** : étudiant souhaitant piloter Proxmox par du code Terraform / OpenTofu.

Votre compte étudiant dispose d'un **token API Proxmox** dédié.
Il vous permet d'utiliser le provider [bpg/proxmox](https://registry.terraform.io/providers/bpg/proxmox)
pour créer et gérer vos VMs sans toucher aux ressources des autres.

---

## Vos identifiants

L'administrateur vous a remis un fichier (ou une ligne de `credentials.csv`) contenant :

| Champ          | Exemple                          | Description                        |
|----------------|----------------------------------|------------------------------------|
| `userid`       | `jdupont@pve`                    | Votre compte Proxmox               |
| `token_id`     | `jdupont@pve!labomatics`         | Identifiant complet du token API   |
| `token_secret` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxx`   | Secret du token (à ne pas partager)|
| `wan_ip`       | `172.29.20.18`                   | Votre IP WAN sur le réseau du lab  |

> Le token a **les mêmes droits que votre compte** (privsep=0) :
> accès à votre pool, au pool template, et à votre VNet VXLAN.

---

## Configuration du provider

```hcl
terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.78"
    }
  }
}

provider "proxmox" {
  endpoint  = "https://<proxmox-host>:8006/"
  api_token = "jdupont@pve!labomatics=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  insecure  = true   # si le certificat Proxmox est auto-signé
}
```

> Remplacez `<proxmox-host>` par l'adresse fournie par l'admin,
> et le token par vos valeurs réelles.

### Avec des variables d'environnement (recommandé)

Évitez de stocker le secret en clair dans un fichier `.tf` :

```bash
export PROXMOX_VE_ENDPOINT="https://<proxmox-host>:8006/"
export PROXMOX_VE_API_TOKEN="jdupont@pve!labomatics=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export PROXMOX_VE_INSECURE="true"
```

```hcl
provider "proxmox" {}  # lit les variables d'environnement automatiquement
```

---

## Votre pool et le pool template

### Pool personnel

Toutes vos ressources doivent être créées dans votre **pool personnel** (`jdupont`).
Les ressources hors pool ne seront pas visibles depuis votre compte.

```hcl
resource "proxmox_virtual_environment_vm" "ma_vm" {
  # ...
  pool_id = "jdupont"   # votre pool personnel
}
```

### Pool template

Le pool `template` contient les images de base fournies par l'administrateur.
Vous pouvez cloner ces templates mais pas les modifier.

Pour lister les templates disponibles :

```
Proxmox UI → Datacenter → pool → template
```

---

## Cloner une template

La façon la plus courante de créer une VM est de **cloner une template** du pool `template`.

```hcl
# Récupère la template par son VMID (fourni par l'admin, ex. 90200 pour OpenWrt)
data "proxmox_virtual_environment_vm" "template" {
  node_name = "pve-node1"   # nœud où se trouve la template
  vm_id     = 90200
}

resource "proxmox_virtual_environment_vm" "ma_vm" {
  name      = "ma-vm-jdupont"
  node_name = "pve-node1"
  pool_id   = "jdupont"

  clone {
    vm_id = data.proxmox_virtual_environment_vm.template.vm_id
    full  = true    # clone complet (indépendant de la template)
  }

  cpu {
    cores = 2
  }

  memory {
    dedicated = 2048   # en Mo
  }

  disk {
    datastore_id = "local-lvm"   # stockage indiqué par l'admin
    interface    = "scsi0"
    size         = 20            # en Go
  }

  network_device {
    bridge = "vn00018"   # votre VNet VXLAN (voir section suivante)
  }
}
```

---

## Connecter une VM à votre réseau VXLAN

Votre VNet VXLAN s'appelle `vn0XXXXX` où `XXXXX` est votre `id` sur 5 chiffres
(ex. id=18 → `vn00018`).

```hcl
network_device {
  bridge = "vn00018"   # remplacez par votre VNet
  model  = "virtio"
}
```

> L'administrateur peut vous confirmer le nom exact de votre VNet avec
> `labomatics find <votre-nom>`.

---

## Créer un conteneur LXC

```hcl
resource "proxmox_virtual_environment_container" "mon_ct" {
  description = "Mon conteneur"
  node_name   = "pve-node1"
  pool_id     = "jdupont"

  initialization {
    hostname = "mon-conteneur"

    ip_config {
      ipv4 {
        address = "10.100.18.10/24"   # IP dans votre subnet VXLAN
        gateway = "10.100.18.1"       # votre OpenWrt fait passerelle
      }
    }
  }

  network_interface {
    name   = "eth0"
    bridge = "vn00018"
  }

  operating_system {
    template_file_id = "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
    type             = "debian"
  }

  cpu {
    cores = 1
  }

  memory {
    dedicated = 512
    swap      = 256
  }

  disk {
    datastore_id = "local-lvm"
    size         = 8
  }
}
```

---

## Limites de votre compte

Le provider vous donne accès uniquement aux ressources de votre pool.
Les opérations hors périmètre retournent une erreur `403 Permission denied`.

| Action                              | Autorisé |
|-------------------------------------|----------|
| Créer/supprimer des VMs dans votre pool | ✓    |
| Cloner les templates du pool `template` | ✓    |
| Modifier les templates              | ✗        |
| Créer des VMs dans un autre pool    | ✗        |
| Modifier la config réseau (VNet)    | ✗        |
| Accéder aux ressources des autres   | ✗        |

---

## Exemple minimal complet

```hcl
terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.78"
    }
  }
}

provider "proxmox" {}   # via variables d'environnement

resource "proxmox_virtual_environment_vm" "debian" {
  name      = "debian-jdupont"
  node_name = "pve-node1"
  pool_id   = "jdupont"

  clone {
    vm_id = 90201   # VMID de la template Debian (demandez à l'admin)
    full  = true
  }

  cpu    { cores = 2 }
  memory { dedicated = 2048 }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 20
  }

  network_device {
    bridge = "vn00018"
    model  = "virtio"
  }
}
```

```bash
export PROXMOX_VE_ENDPOINT="https://192.168.1.10:8006/"
export PROXMOX_VE_API_TOKEN="jdupont@pve!labomatics=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export PROXMOX_VE_INSECURE="true"

terraform init
terraform plan
terraform apply
```

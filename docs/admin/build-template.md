# Build de templates cloud-init

> **Audience** : administrateur Proxmox

La commande `labomatics template build` construit des templates Linux (Ubuntu, Debian,
Fedora, Alpine…) directement via l'API Proxmox, sans Packer ni SSH vers les VMs.

---

## Pipeline

Pour chaque template définie dans `infra.yaml` :

1. Suppression de la template existante (si le VMID est déjà utilisé)
2. Suppression de l'image déjà téléchargée (si présente)
3. **Téléchargement** de l'image cloud via l'API Proxmox (`download-url`)
4. **virt-customize** — pré-installation des packages (SSH root@nœud, libguestfs-tools)
5. **Création de la VM** avec import-from + drive cloud-init
6. Redimensionnement du disque
7. **Démarrage** de la VM + attente du guest agent
8. **Shutdown** propre (force stop si timeout)
9. Nettoyage de l'image téléchargée
10. **Conversion en template** + ajout au pool `template`

> Les étapes 7–8 sont ignorées si `cloudinit: false` (ex: OPNsense).

---

## Prérequis

- **SSH root** vers le nœud Proxmox depuis la machine qui exécute `labomatics`
  (nécessaire uniquement si `default_packages` ou `extra_packages` sont définis)
- `libguestfs-tools` sur le nœud — installé automatiquement si absent
- Stockage `iso_storage_pool` de type **directory** (ex: `local`)

---

## Commande

```bash
# Toutes les templates définies dans infra.yaml
labomatics template build

# Une ou plusieurs templates spécifiques
labomatics template build ubuntu-25.10
labomatics template build ubuntu-25.10,debian-13

# Sans confirmation interactive
labomatics template build --yes
```

---

## Configuration infra.yaml

```yaml
templates:
  default_user: labomatics    # utilisateur cloud-init dans toutes les templates
  default_pass: changeme      # mot de passe cloud-init par défaut

  # Packages installés dans TOUTES les templates via virt-customize.
  # Désactiver par template avec download_packages: false.
  default_packages:
    - qemu-guest-agent

  sources:
    - name: ubuntu-25.10          # identifiant (utilisé par la CLI)
      vmid: 90100                 # VMID Proxmox (doit être libre)
      storage_pool: local-lvm    # stockage pour le disque VM
      iso_storage_pool: local    # stockage directory pour l'image téléchargée
      iso_url: "https://..."      # URL de l'image cloud
      iso_filename: "nom.qcow2"  # optionnel — renomme le fichier local
                                  # (nécessaire si l'URL se termine en .img ou .bz2)
      memory: 2048               # RAM en MB (build uniquement)
      cores: 2                   # vCPUs (build uniquement)
      disk_size: "10G"           # taille finale du disque
      # Optionnel :
      node: pve                  # nœud cible (défaut: nœud le plus libre)
      cloud_init_user: admin     # surcharge default_user pour cette template
      cloud_init_password: xxx   # surcharge default_pass pour cette template
      cpu_type: kvm64            # type CPU Proxmox (défaut: x86-64-v2-AES)
      boot_timeout: 300          # timeout guest agent en secondes (défaut: 300)
      ostype: l26                # type OS Proxmox (défaut: l26)
      cloudinit: false           # désactive cloud-init + boot (ex: OPNsense/FreeBSD)
      download_packages: false   # désactive virt-customize pour cette template
      extra_packages:            # packages supplémentaires (ajoutés à default_packages)
        - nano
        - vim
```

### Champs importants

| Champ | Défaut | Description |
|---|---|---|
| `iso_url` | — | URL de l'image cloud à télécharger |
| `iso_filename` | déduit de l'URL | Nom de fichier local. **Obligatoire** si l'URL se termine en `.img` (renommer en `.qcow2`) ou si le téléchargement décompresse un `.bz2` (indiquer le nom final en `.raw`) |
| `cloudinit` | `true` | `false` = pas de drive cloud-init, pas de boot (FreeBSD, pfSense…) |
| `download_packages` | `true` | `false` = skip virt-customize pour cette template |
| `default_packages` | `[]` | Défini dans `templates:`, s'applique à **toutes** les sources |
| `extra_packages` | `[]` | Défini dans `sources.$template`, s'ajoute à `default_packages` |
| `cpu_type` | `x86-64-v2-AES` | `kvm64` recommandé pour Alpine (meilleure compatibilité) |
| `boot_timeout` | `300` | Augmenter pour Alpine (boot lent via OpenRC) |

### Notes sur les extensions de fichier

Proxmox valide l'extension du fichier lors du téléchargement :

| Extension | Content type | Stockage |
|---|---|---|
| `.iso` | iso | `{path}/template/iso/` |
| `.qcow2`, `.vmdk`, `.raw`, `.vhd` | import | `{path}/template/import/` |
| `.img` | **rejeté** | — utiliser `iso_filename` pour renommer en `.qcow2` |
| `.bz2` (auto-décompressé) | — | indiquer le nom final dans `iso_filename` |

---

## Templates par défaut

| Template | Image | Particularité |
|---|---|---|
| `ubuntu-25.10` | Ubuntu 25.10 Cloud | `iso_filename` requis (`.img` → `.qcow2`) |
| `debian-13` | Debian 13 genericcloud | `extra_packages: [nano, curl, wget, vim]` |
| `fedora-43` | Fedora 43 Cloud | `download_packages: false` (GA inclus) |
| `alpine-3` | Alpine 3.21 nocloud | `cpu_type: kvm64`, `boot_timeout: 600` |
| `opnsense-25` | OPNsense 25.1 nano | `cloudinit: false`, `download_packages: false` |

---

## Troubleshooting

**`400 Bad Request: invalid filename or wrong extension`**
: L'URL se termine en `.img`. Ajouter `iso_filename: "nom.qcow2"` dans la config.

**`Image is not in qcow2 format`**
: L'image est en format raw (ex: OPNsense nano). Utiliser `iso_filename: "nom.raw"`.

**`virt-customize: No such file or directory`**
: Le chemin de l'image est introuvable. Vérifier que `iso_storage_pool` est bien un
  stockage de type `dir` et que le fichier a été téléchargé.

**`you can't convert a VM to template if VM is running`**
: Le shutdown n'a pas eu le temps de se terminer. Labomatics réessaie automatiquement
  3 fois avec force stop. Si l'erreur persiste, vérifier l'état de la VM dans Proxmox.

**Timeout guest agent**
: L'image n'inclut pas `qemu-guest-agent`. S'assurer que `default_packages` ou
  `extra_packages` contient `qemu-guest-agent`, ou ajouter `download_packages: false`
  si virt-customize ne fonctionne pas pour cette image.

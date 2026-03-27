# Déploiement de TPs

> **Audience** : administrateur du lab Proxmox.

Les commandes `student deploy` et `student undeploy` permettent de déployer et supprimer
des VMs de travaux pratiques dans le pool de chaque étudiant à partir d'un fichier YAML.

---

## Principe

Un TP est un ensemble de VMs clonées depuis des templates Proxmox existantes.
Chaque étudiant reçoit sa propre copie des VMs dans son pool dédié.

- **net0** de chaque VM est toujours connecté au VNet VXLAN de l'étudiant (réseau LAN privé)
- Des interfaces supplémentaires (net1, net2…) peuvent être ajoutées via `extra_nics`
- Les VMs sont identifiées par un tag Proxmox `labomatics-tp:<nom>` + un bloc dans leur description
- La commande est **idempotente** : une VM déjà déployée avec la même configuration est ignorée

---

## Commandes

```bash
# Déployer un TP
labomatics student deploy -f tp-opnsense.yaml

# Déployer sans confirmation, avec 4 workers parallèles
labomatics student deploy -f tp-opnsense.yaml --workers 4 --yes

# Supprimer un TP (via le fichier)
labomatics student undeploy -f tp-opnsense.yaml

# Supprimer un TP (via son nom uniquement)
labomatics student undeploy --tp tp-opnsense --yes
```

---

## Format du fichier TP YAML

```yaml
name: tp-opnsense               # identifiant unique du TP (utilisé pour les tags Proxmox)
description: "TP OPNsense S2"   # optionnel, informatif
target_classes:                 # optionnel — liste de classes ciblées
  - M1_SRC                      # si absent, tous les étudiants du CSV sont ciblés
  - M2_SEC

vms:
  - name: opnsense              # nom de la VM (préfixé par le login étudiant)
    template: 90110             # VMID de la template Proxmox source
    memory: 8164                # RAM en MB
    cores: 4                    # vCPUs
    disk_size: "30G"            # optionnel — redimensionne le disque après le clone
    start: false                # démarrer la VM après création (défaut: false)

    cloud_init:                 # optionnel — surcharge les credentials cloud-init
      user: admin
      password: changeme

    extra_nics:                 # interfaces réseau supplémentaires (net1, net2…)
      - bridge: vmbr0           # bridge Proxmox (WAN, ou autre bridge physique)
        model: virtio           # modèle de carte réseau (défaut: virtio)

  - name: client-linux
    template: 90100
    memory: 2048
    cores: 2
    start: true
```

### Champs de la VM

| Champ         | Obligatoire | Défaut    | Description                                                  |
|---------------|-------------|-----------|--------------------------------------------------------------|
| `name`        | oui         | —         | Nom de la VM (suffixé au login de l'étudiant dans Proxmox)  |
| `template`    | oui         | —         | VMID de la template source à cloner                         |
| `memory`      | non         | `512`     | RAM en MB                                                    |
| `cores`       | non         | `1`       | Nombre de vCPUs                                              |
| `disk_size`   | non         | —         | Taille finale du disque (ex: `"20G"`) — `null` = pas de resize |
| `start`       | non         | `false`   | Démarrer la VM immédiatement après création                  |
| `cloud_init`  | non         | —         | Credentials cloud-init (user, password)                      |
| `extra_nics`  | non         | `[]`      | Interfaces réseau supplémentaires (net1+)                    |

### Réseau automatique

`net0` est toujours connecté au VNet VXLAN de l'étudiant — aucune configuration nécessaire.
Les `extra_nics` définissent `net1`, `net2`… dans l'ordre de la liste.

---

## Idempotence

Lors d'un re-déploiement, labomatics compare un hash de la configuration de chaque VM
(template, mémoire, CPUs, disque, cloud-init, extra_nics) avec celui stocké dans la
description de la VM Proxmox.

| Situation                              | Comportement                        |
|----------------------------------------|-------------------------------------|
| VM absente                             | Créée depuis la template            |
| VM présente, même configuration        | Ignorée (aucune modification)       |
| VM présente, configuration différente  | Supprimée + recrée depuis la template |

---

## Suivi des VMs de TP dans Proxmox

Chaque VM déployée par `student deploy` reçoit :

- Un **tag Proxmox** : `labomatics-tp:<nom-du-tp>` (ex: `labomatics-tp:tp-opnsense`)
- Un **bloc dans sa description** :

```
--- labomatics ---
tp: tp-opnsense
student_id: 18
vm: opnsense
config_hash: a3f9c2d1
--- end labomatics ---
```

`student undeploy` utilise ce tag pour retrouver et supprimer toutes les VMs du TP,
quel que soit le nœud ou le pool Proxmox sur lequel elles se trouvent.

---

## Exemple complet — TP OPNsense

```yaml
name: tp-opnsense-s2-2026
description: "TP Firewall OPNsense — Semestre 2 2026"
target_classes:
  - M1_SRC

vms:
  - name: opnsense
    template: 90110        # template opnsense-25 (cloudinit: false)
    memory: 8164
    cores: 4
    disk_size: "30G"
    extra_nics:
      - bridge: vmbr0      # WAN physique
        model: virtio

  - name: client
    template: 90100        # template ubuntu-25.10
    memory: 2048
    cores: 2
    start: true
    cloud_init:
      user: labomatics
      password: changeme
```

Déploiement :

```bash
labomatics student deploy -f tp-opnsense-s2-2026.yaml --yes
```

Résultat pour l'étudiant `jdupont` (id=18) :
- `jdupont-opnsense` (VMID auto) dans le pool `jdupont`, net0=`vn00018`, net1=`vmbr0`
- `jdupont-client` (VMID auto) dans le pool `jdupont`, net0=`vn00018`, démarrée

Suppression en fin de TP :

```bash
labomatics student undeploy --tp tp-opnsense-s2-2026 --yes
```

---

## Troubleshooting

**La VM est recréée à chaque deploy alors qu'elle n'a pas changé**
: Vérifier que la description de la VM contient bien le bloc `--- labomatics ---`.
  Si la VM a été modifiée manuellement dans Proxmox, le bloc peut avoir été effacé.

**`template VMID 90110 introuvable`**
: La template source n'existe pas sur le cluster. Construire les templates avec
  `labomatics template build` ou `labomatics template openwrt`.

**Timeout lors du clone**
: Le clone cross-node nécessite un stockage partagé. Vérifier que la template est
  sur un stockage accessible depuis tous les nœuds (Ceph, NFS, ZFS partagé).

**VMs déployées sur un seul nœud**
: labomatics sélectionne le nœud avec le plus de mémoire libre. En cas de déséquilibre,
  les workers parallèles (`--workers`) répartissent les créations entre étudiants.

# Vue d'ensemble — esgilabs

> **Audience** : administrateur du lab Proxmox.

`esgilabs` est un outil CLI Python qui synchronise un cluster Proxmox avec un fichier
CSV d'étudiants. Il crée et supprime automatiquement, pour chaque étudiant, l'ensemble
des ressources Proxmox nécessaires à son environnement de lab réseau.

---

## Ce que le script provisionne par étudiant

| Ressource         | Valeur                           | Identifiant stable              |
|-------------------|----------------------------------|---------------------------------|
| **Pool Proxmox**  | `nom`                            | `student.nom`                   |
| **VNet VXLAN**    | `vn{id:05d}` (ex. `vn00018`)     | `student.id`                    |
| **Tag VXLAN**     | `id`                             | `student.id`                    |
| **VMID**          | `vmid_start + id`                | `student.id`                    |
| **IP WAN**        | `wan_subnet + id`                | `student.id`                    |
| **Subnet VXLAN**  | `vxlan_pool + id × 256` → `/24`  | `student.id`                    |
| **Compte Proxmox**| `nom@pve`                        | `student.nom`                   |
| **ACL**           | Voir [Droits d'accès](#droits-dacces) | —                          |

> **Clé de stabilité** : toutes les allocations sont basées sur l'`id` CSV de l'étudiant,
> pas sur sa position dans le fichier. Ajouter ou supprimer un étudiant ne réalloue
> pas les ressources des autres.

---

## Architecture réseau

```
Internet
    │
    ▼
[vmbr0 — WAN]  172.16.0.0/24
    │               │
    │        ┌──────┴──────┐
    │        │             │
    ▼        ▼             ▼
 openwrt-  openwrt-     openwrt-
 jdupont   mkorniev     ...
 .18       .240         .N
    │        │
    │        │  VXLAN overlay (tag = student.id)
    ▼        ▼
 vn00018   vn00240
 10.100.18.0/24   10.100.240.0/24
    │        │
 (LAN de   (LAN de
  jdupont)  mkorniev)
```

Chaque VM OpenWrt fait office de routeur entre son subnet VXLAN (LAN) et le WAN physique.
Les VMs peuvent se parler via le WAN ou via des routes inter-VXLAN si l'administrateur
configure des routes supplémentaires.

---

## Droits d'accès

Chaque étudiant dispose d'un compte Proxmox local (`nom@pve`) avec des droits
limités à ses propres ressources :

| Chemin ACL                          | Rôle(s)                             | Effet                                |
|-------------------------------------|-------------------------------------|--------------------------------------|
| `/sdn/zones/{zone}/{vnet}`          | `PVESDNUser`                        | Accès au VNet VXLAN personnel        |
| `/storage`                          | `PVEDatastoreUser` (propagate)      | Lecture des datastores               |
| `/pool/{template_pool}`             | `PVETemplateUser`, `PVEPoolUser`    | Accès en lecture aux templates       |
| `/pool/{userpool}`                  | `PVETemplateUser`, `PVEPoolUser`, `PVEVMAdmin` | Administration de ses VMs |

Le pool template (`template` par défaut) est un pool Proxmox global contenant toutes les
templates du lab. Les étudiants peuvent les voir et les cloner dans leur propre pool.

---

## Flux d'exécution — `apply`

```
CSV étudiants
     │
     ▼
Charger config (infra.yaml + .env)
     │
     ▼
Lister les pools gérés (comment == "esgilabs-managed")
     │
     ▼
Calculer le diff (to_add, to_remove)
     │
     ├─ Afficher tableau de confirmation
     │
     └─ Après confirmation :
         │
         ├─ REMOVES (pour chaque pool à supprimer) :
         │   ├── Arrêter + supprimer VMs QEMU (wait_for_task)
         │   ├── Arrêter + supprimer LXC (wait_for_task)
         │   ├── Révoquer ACL + supprimer user@pve
         │   ├── Supprimer VNet SDN + apply_sdn
         │   └── Supprimer pool
         │
         └─ ADDS (pour chaque étudiant à créer) :
             ├── Créer pool + VNet (batch)
             ├── apply_sdn
             ├── Créer user@pve + ACL
             ├── Écrire credentials.csv
             └── Cloner template → cloud-init → démarrer VM
```

---

## Sélection automatique du nœud

Plutôt que de cibler un nœud fixe, le script interroge le cluster à chaque déploiement
et sélectionne le nœud avec le plus de mémoire libre (`pick_node`).

**Prérequis** : la template OpenWrt doit être sur un **stockage partagé** entre tous les
nœuds (Ceph RBD, NFS, ZFS over iSCSI, etc.). Voir [template.md](template.md).

Pour la destruction, le nœud est lu depuis les métadonnées du membre de pool (champ
`node`), ce qui permet de gérer des VMs réparties sur plusieurs nœuds.

---

## Idempotence

Le script est idempotent : une deuxième exécution avec le même CSV ne fait rien
(les pools existants ne sont pas recréés). Les cas suivants sont gérés :

- VM déjà déployée → ignorée avec avertissement
- Utilisateur Proxmox déjà créé → ACL reconfigurées sans recréer le compte
- Mot de passe déjà dans `credentials.csv` → conservé (non regénéré)

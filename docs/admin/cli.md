# Référence CLI

> **Audience** : administrateur du lab Proxmox.

```bash
labomatics <groupe> <commande> [options]
```

---

## Vue d'ensemble des groupes

| Groupe      | Description                                       |
|-------------|---------------------------------------------------|
| `setup`     | Assistant d'installation interactif               |
| `student`   | Gestion des étudiants (apply, diff, deploy…)      |
| `pool`      | Pools Proxmox et utilisation des IPs              |
| `sdn`       | Inspection SDN (zones, vnets)                     |
| `template`  | Construction des templates Proxmox                |

---

## `setup` — Assistant d'installation

Lance le wizard complet : saisie credentials, copie des fichiers de config,
vérification Proxmox, ouverture de `infra.yaml`, vérification bridges/storages/SDN,
création du pool template, conseil SPICE et build OpenWrt optionnel.

```bash
labomatics setup
labomatics setup --dir ./config   # répertoire de configuration alternatif
```

---

## `student` — Gestion des étudiants

### `student apply` — Synchroniser Proxmox avec le CSV

Calcule le diff entre le CSV et l'état Proxmox, affiche un tableau de confirmation,
puis applique les changements.

```bash
labomatics student apply
labomatics student apply --yes              # sans confirmation (CI/CD)
labomatics student apply --recheck-all      # recrée users/tokens/ACL manquants
labomatics student apply --classe M1_SRC    # restreint à une classe
```

**Pour chaque ajout :**
1. Crée le pool Proxmox
2. Crée le VNet SDN + subnet VXLAN
3. Applique la configuration SDN
4. Crée le compte utilisateur `nom@pve` + token API + ACL
5. Clone la template → configure cloud-init → démarre la VM
6. Met à jour `credentials.csv`

**Pour chaque suppression :**
1. Arrête et supprime les VMs QEMU + LXC du pool
2. Révoque les ACL + supprime le compte `nom@pve` + token
3. Supprime le VNet SDN
4. Supprime le pool

---

### `student diff` — Aperçu des changements (lecture seule)

```bash
labomatics student diff
labomatics student diff --classe M1_SRC
```

Exemple de sortie :

```
  3 étudiant(s) — students.csv

 Changements à appliquer
 ──────────────────────────────────────────────────────────────
   +   jdupont      10018   172.16.0.18   10.100.18.0/24  vn00018
   +   asmith       10042   172.16.0.42   10.100.42.0/24  vn00042
   −   ancien_user   —       —             —               —

  + 2 à créer   − 1 à supprimer
```

---

### `student list` — Lister les VMs des pools étudiants

```bash
labomatics student list
labomatics student list --pool jdupont
labomatics student list --classe M1_SRC
```

---

### `student status` — Consommation par étudiant

Affiche CPU / RAM / disk consommés par chaque étudiant, comparés à son flavor.

```bash
labomatics student status
labomatics student status --classe M1_SRC
```

---

### `student find` — Rechercher un étudiant

Retrouve un étudiant par son IP WAN, le nom de son VNet ou son nom d'utilisateur.

```bash
labomatics student find 172.16.0.18      # par IP WAN
labomatics student find vn00018          # par nom de VNet
labomatics student find jdupont          # par nom d'utilisateur
labomatics student find jdupont --classe M1_SRC
```

---

### `student creds` — Afficher les credentials

Affiche le contenu de `credentials.csv` sous forme de tableau.

```bash
labomatics student creds
labomatics student creds --classe M1_SRC
```

> Les mots de passe sont affichés en clair — ne pas utiliser dans un contexte partagé.

---

### `student recreate` — Recréer la VM d'un étudiant

Détruit la VM OpenWrt et la redéploie depuis la template (nouvelle IP possible).

```bash
labomatics student recreate jdupont
labomatics student recreate jdupont --yes
```

---

### `student deploy` — Déployer un TP

Déploie les VMs définies dans un fichier YAML pour les étudiants ciblés.

```bash
labomatics student deploy -f tp-opnsense.yaml
labomatics student deploy -f tp-opnsense.yaml --workers 4 --yes
```

Voir la structure du fichier TP YAML dans la section dédiée.

---

### `student undeploy` — Supprimer un TP

Supprime toutes les VMs d'un TP (par fichier ou par nom).

```bash
labomatics student undeploy -f tp-opnsense.yaml
labomatics student undeploy --tp tp-opnsense-s2-2026 --yes
```

---

### `student destroy` — Supprimer tous les étudiants

Supprime toutes les ressources de **tous** les étudiants gérés (VMs, VNets, ACL, pools).

```bash
labomatics student destroy
labomatics student destroy --yes
```

---

## `pool` — Gestion des pools

### `pool list` — Lister les pools gérés

```bash
labomatics pool list
```

### `pool ips` — État des pools IP

Affiche le taux d'utilisation du pool WAN et VXLAN.

```bash
labomatics pool ips
```

---

## `sdn` — Inspection SDN

### `sdn zones`

```bash
labomatics sdn zones
```

### `sdn vnets`

```bash
labomatics sdn vnets
labomatics sdn vnets --zone esgilab
```

---

## `template` — Construction des templates

### `template build` — Templates cloud-init

Construit les templates Linux définies dans `infra.yaml`.

```bash
labomatics template build
labomatics template build ubuntu-25.10
labomatics template build ubuntu-25.10,debian-13
labomatics template build --yes
```

### `template build-openwrt` — Template OpenWrt

Télécharge la dernière version stable d'OpenWrt, la configure et la convertit
en template Proxmox. À exécuter **en root sur un nœud Proxmox**.

```bash
labomatics template build-openwrt
labomatics template build-openwrt --version 24.10.0 --vmid 90200 --storage zfs-store
```

| Option         | Défaut                         | Description                         |
|----------------|--------------------------------|-------------------------------------|
| `--version`    | Dernière stable (auto-détecté) | Version OpenWrt                     |
| `--vmid`       | `infra.yaml → template_vmid`   | VMID Proxmox                        |
| `--storage`    | `infra.yaml → storage`         | Stockage cible                      |
| `--password`   | `openwrt`                      | Mot de passe root injecté           |
| `--template-pool` | `template`                  | Pool Proxmox d'accueil              |

Voir [template.md](template.md) pour le détail des opérations.

---

## Options communes

| Option        | Commandes concernées       | Description                              |
|---------------|----------------------------|------------------------------------------|
| `--yes, -y`   | apply, recreate, deploy…   | Pas de confirmation interactive          |
| `--classe`    | apply, diff, list, status… | Restreint à une classe (ex: `M1_SRC`)    |
| `--help`      | toutes                     | Affiche l'aide                           |

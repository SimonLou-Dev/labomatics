# Référence CLI

> **Audience** : administrateur du lab Proxmox.

```bash
labomatics <groupe> <commande> [options]
```

---

## Vue d'ensemble des groupes

| Groupe      | Description                                                          |
|-------------|----------------------------------------------------------------------|
| `setup`     | Assistant d'installation interactif                                  |
| `student`   | Gestion des étudiants et de leurs VMs                                |
| `pool`      | Pools Proxmox gérés (quotas, nombre de VMs)                          |
| `network`   | Réseau : zones SDN, VNets VXLAN, utilisation des adresses IP         |
| `template`  | Construction des templates Proxmox (Linux cloud-init, OpenWrt)       |

> **`student list` vs `pool list`**
> - `student list` → liste les **VMs** présentes dans chaque pool étudiant
> - `pool list` → liste les **pools** Proxmox eux-mêmes avec leurs quotas CPU/RAM/disk

---

## `setup` — Assistant d'installation

Lance le wizard complet : saisie credentials, copie des fichiers de config,
vérification Proxmox, ouverture de `infra.yaml`, vérification bridges/storages/SDN,
création du pool template, conseil SPICE et build OpenWrt optionnel.

Le wizard est **idempotent** : si `.env` ou `infra.yaml` existent déjà, ils ne sont pas écrasés.

```bash
labomatics setup
labomatics setup --dir ./config   # répertoire de configuration alternatif
```

---

## `student` — Gestion des étudiants

### `student apply` — Provisionner / mettre à jour

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

Affiche ce que `apply` ferait, sans rien modifier.

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

### `student list` — Lister les VMs dans les pools étudiants

Affiche toutes les VMs (VMID, nom, statut, nœud) présentes dans chaque pool étudiant.
Différent de `pool list` qui affiche les pools et leurs quotas, sans détailler les VMs.

```bash
labomatics student list
labomatics student list --pool jdupont
labomatics student list --classe M1_SRC
```

---

### `student status` — Consommation par étudiant

Affiche CPU / RAM / disk consommés par chaque étudiant, comparés aux limites de son flavor.

```bash
labomatics student status
labomatics student status --classe M1_SRC
```

---

### `student find` — Rechercher un étudiant

Retrouve un étudiant par son IP WAN, le nom de son VNet ou son login.

```bash
labomatics student find 172.16.0.18      # par IP WAN
labomatics student find vn00018          # par identifiant VNet
labomatics student find jdupont          # par login
labomatics student find jdupont --classe M1_SRC
```

---

### `student creds` — Afficher les credentials

Affiche le contenu de `credentials.csv` sous forme de tableau (login, token, IP WAN, VNet).

```bash
labomatics student creds
labomatics student creds --classe M1_SRC
```

> Les mots de passe sont affichés en clair — ne pas utiliser dans un contexte partagé.

---

### `student recreate` — Recréer la VM OpenWrt d'un étudiant

Supprime la VM OpenWrt existante et la recrée depuis la template (nouvelle IP possible).
Utile après une corruption ou une mauvaise configuration réseau.

```bash
labomatics student recreate jdupont
labomatics student recreate jdupont --yes
```

---

### `student deploy` — Déployer un TP

Déploie les VMs définies dans un fichier YAML pour chaque étudiant.
La commande est **idempotente** : les VMs déjà déployées avec la même configuration sont ignorées ;
celles dont la configuration a changé sont supprimées et recrées.

```bash
labomatics student deploy -f tp-opnsense.yaml
labomatics student deploy -f tp-opnsense.yaml --workers 4 --yes
```

Voir [deploy.md](deploy.md) pour le format du fichier YAML et les exemples complets.

---

### `student undeploy` — Supprimer un TP

Supprime toutes les VMs d'un TP (identifiées par leur tag Proxmox).

```bash
labomatics student undeploy -f tp-opnsense.yaml
labomatics student undeploy --tp tp-opnsense-s2-2026 --yes
```

---

### `student destroy` — Supprimer tous les étudiants

Supprime toutes les ressources de **tous** les étudiants gérés (VMs, VNets, ACL, pools).
Action irréversible.

```bash
labomatics student destroy
labomatics student destroy --yes
```

---

## `pool` — Pools Proxmox

Liste les pools Proxmox créés par labomatics avec leurs quotas et le nombre de VMs.
Pour voir le détail des VMs à l'intérieur, utilisez `student list`.

### `pool list`

```bash
labomatics pool list
```

---

## `network` — Réseau SDN et IPs

### `network zones` — Zones SDN

Liste toutes les zones SDN (VXLAN, Simple…) configurées dans le datacenter.

```bash
labomatics network zones
```

### `network vnets` — VNets VXLAN

Liste les VNets SDN. Chaque étudiant dispose d'un VNet dédié (ex: `vn00018`).

```bash
labomatics network vnets
labomatics network vnets --zone esgilab
```

### `network ips` — Utilisation des pools IP

Affiche le taux d'utilisation des plages IP WAN et VXLAN définies dans `infra.yaml`.

```bash
labomatics network ips
```

---

## `template` — Construction des templates

### `template build` — Templates Linux cloud-init

Construit les templates Linux définies dans `infra.yaml` (Ubuntu, Debian, Fedora, Alpine…).

```bash
labomatics template build
labomatics template build ubuntu-25.10
labomatics template build ubuntu-25.10,debian-13
labomatics template build --yes
```

### `template openwrt` — Template OpenWrt

Télécharge la dernière version stable d'OpenWrt, la configure et la convertit
en template Proxmox. À exécuter **en root sur un nœud Proxmox**.
Cette template est clonée pour chaque étudiant lors de `student apply`.

```bash
labomatics template openwrt
labomatics template openwrt --version 24.10.0 --vmid 90200 --storage zfs-store
```

| Option            | Défaut                         | Description                         |
|-------------------|--------------------------------|-------------------------------------|
| `--version`       | Dernière stable (auto-détecté) | Version OpenWrt                     |
| `--vmid`          | `infra.yaml → template_vmid`   | VMID Proxmox                        |
| `--storage`       | `infra.yaml → storage`         | Stockage cible                      |
| `--password`      | `openwrt`                      | Mot de passe root injecté           |
| `--template-pool` | `template`                     | Pool Proxmox d'accueil              |

Voir [template.md](template.md) pour le détail des opérations.

---

## Options communes

| Option        | Commandes concernées              | Description                              |
|---------------|-----------------------------------|------------------------------------------|
| `--yes, -y`   | apply, recreate, deploy, destroy… | Sans confirmation interactive            |
| `--classe`    | apply, diff, list, status, find…  | Restreint à une classe (ex: `M1_SRC`)    |
| `--help`      | toutes                            | Affiche l'aide détaillée de la commande  |

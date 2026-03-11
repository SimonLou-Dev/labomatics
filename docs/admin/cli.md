# Référence CLI

> **Audience** : administrateur du lab Proxmox.

```bash
labomatics <commande> [options]
```

---

## `apply` — Synchroniser Proxmox avec le CSV

Calcule le diff entre le CSV et l'état Proxmox, affiche un tableau de confirmation,
puis applique les changements.

```bash
labomatics apply
labomatics apply --yes   # Pas de confirmation interactive (CI/CD)
```

**Pour chaque ajout :**
1. Crée le pool Proxmox
2. Crée le VNet SDN + subnet VXLAN
3. Applique la configuration SDN
4. Crée le compte utilisateur `nom@pve` + configure les ACL
5. Clone la template → configure cloud-init → démarre la VM
6. Met à jour `credentials.csv`

**Pour chaque suppression :**
1. Arrête et supprime les VMs QEMU du pool (y compris les templates)
2. Arrête et supprime les LXC du pool
3. Révoque les ACL + supprime le compte `nom@pve`
4. Supprime le VNet SDN + applique SDN
5. Supprime le pool

---

## `diff` — Aperçu des changements (lecture seule)

Affiche le diff CSV ↔ Proxmox sans rien modifier.

```bash
labomatics diff
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

## `recreate` — Recréer un étudiant

Détruit toutes les ressources d'un étudiant et les recrée (nouvelle IP allouée).

```bash
labomatics recreate jdupont
```

Utile pour réinitialiser un environnement corrompu sans toucher aux autres.

---

## `status` — Consommation par tenant

Affiche CPU / RAM / disk consommés par chaque étudiant, comparés à son flavor.

```bash
labomatics status
```

---

## `ips` — État des pools IP

Affiche le taux d'utilisation du pool WAN et VXLAN.

```bash
labomatics ips
```

---

## `pools` — Lister les pools gérés

Affiche tous les pools Proxmox créés par labomatics (marqueur `labomatics-managed`).

```bash
labomatics pools
```

Colonnes : Pool, VMs (QEMU), LXC, liste des membres QEMU.

---

## `zones` — Lister les zones SDN

Affiche toutes les zones SDN du cluster avec leur type et état.

```bash
labomatics zones
```

---

## `vnets` — Lister les VNets SDN

Affiche les VNets dans la zone par défaut (configurée dans `infra.yaml`) ou une
zone spécifique.

```bash
labomatics vnets
labomatics vnets --zone esgilab
```

Colonnes : VNet, Zone, Tag VXLAN, Pool associé (= alias du VNet).

---

## `vms` — Lister les VMs des pools gérés

Affiche toutes les VMs QEMU des pools gérés, ou celles d'un pool spécifique.

```bash
labomatics vms
labomatics vms --pool jdupont
```

Colonnes : VM, VMID, Pool, Node, Status.

---

## `find` — Rechercher un étudiant

Retrouve un étudiant par son IP WAN, le nom de son VNet ou son nom d'utilisateur.
Affiche ses informations réseau et l'état live de sa VM sur Proxmox.

```bash
labomatics find 172.16.0.18      # par IP WAN
labomatics find vn00018          # par nom de VNet
labomatics find jdupont          # par nom d'utilisateur
```

Exemple de sortie :

```
╭─────── jdupont ───────╮
│ Nom           jdupont │
│ ID            18      │
│ User Proxmox  jdupont@pve │
│ VMID          10018   │
│ Pool          jdupont │
│ WAN IP        172.16.0.18 │
│ VXLAN subnet  10.100.18.0/24 │
│ VXLAN IP      10.100.18.1 │
│ VXLAN gateway 10.100.18.254 │
│ VNet          vn00018 │
│ Pool Proxmox  ✓ existe │
│ VM status     running (pve-a-1) │
╰───────────────────────╯
```

---

## `credentials` — Afficher les credentials générés

Affiche le contenu de `credentials.csv` sous forme de tableau.

```bash
labomatics credentials
```

> Les mots de passe sont affichés en clair — ne pas utiliser dans un contexte partagé.

---

## `build-openwrt` — Créer la template OpenWrt

Télécharge la dernière version stable d'OpenWrt, la configure et la convertit en
template Proxmox. Doit être exécuté **en root sur un nœud Proxmox**.

```bash
# Version automatique (dernière stable), vmid et storage depuis infra.yaml
labomatics build-openwrt

# Paramètres explicites
labomatics build-openwrt --version 24.10.0 --vmid 90200 --storage zfs-store --password openwrt
```

| Option        | Défaut                         | Description                                   |
|---------------|--------------------------------|-----------------------------------------------|
| `--version`   | Dernière stable (auto-détecté) | Version OpenWrt à télécharger                 |
| `--vmid`      | `infra.yaml → template_vmid`   | VMID Proxmox de la template                   |
| `--storage`   | `infra.yaml → storage`         | Stockage cible                                |
| `--password`  | `openwrt`                      | Mot de passe root injecté dans l'image        |

Voir [template.md](template.md) pour le détail des opérations.

---

## `init` — Initialiser la configuration

Crée `/etc/labomatics/` avec les fichiers de configuration par défaut.

```bash
labomatics init
```

---

## Options globales

| Option     | Description                                      |
|------------|--------------------------------------------------|
| `--help`   | Affiche l'aide (disponible sur chaque commande)  |
| `--yes, -y`| (apply uniquement) Pas de confirmation interactive |

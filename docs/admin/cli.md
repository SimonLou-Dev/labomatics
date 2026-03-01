# Référence CLI

> **Audience** : administrateur du lab Proxmox.

```bash
python -m esgilabs <commande> [options]
```

---

## `apply` — Synchroniser Proxmox avec le CSV

Calcule le diff entre le CSV et l'état Proxmox, affiche un tableau de confirmation,
puis applique les changements.

```bash
python -m esgilabs apply
python -m esgilabs apply --yes   # Pas de confirmation interactive (CI/CD)
```

**Pour chaque ajout :**
1. Crée le pool Proxmox
2. Crée le VNet SDN + subnet VXLAN
3. Applique la configuration SDN
4. Crée le compte utilisateur `nom@pve` + configure les ACL
5. Clone la template → configure cloud-init → démarre la VM
6. Met à jour `credentials.csv`

**Pour chaque suppression :**
1. Arrête et supprime les VMs QEMU du pool (attend la fin de chaque tâche)
2. Arrête et supprime les LXC du pool
3. Révoque les ACL + supprime le compte `nom@pve`
4. Supprime le VNet SDN + applique SDN
5. Supprime le pool

---

## `diff` — Aperçu des changements (lecture seule)

Affiche le diff CSV ↔ Proxmox sans rien modifier.

```bash
python -m esgilabs diff
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

## `pools` — Lister les pools gérés

Affiche tous les pools Proxmox créés par ce script (marqueur `esgilabs-managed`).

```bash
python -m esgilabs pools
```

Colonnes : Pool, VMs (QEMU), LXC, liste des membres QEMU.

---

## `zones` — Lister les zones SDN

Affiche toutes les zones SDN du cluster avec leur type et état.

```bash
python -m esgilabs zones
```

---

## `vnets` — Lister les VNets SDN

Affiche les VNets dans la zone par défaut (configurée dans `infra.yaml`) ou une
zone spécifique.

```bash
python -m esgilabs vnets
python -m esgilabs vnets --zone esgilab
```

Colonnes : VNet, Zone, Tag VXLAN, Pool associé (= alias du VNet).

---

## `vms` — Lister les VMs des pools gérés

Affiche toutes les VMs QEMU des pools gérés, ou celles d'un pool spécifique.

```bash
python -m esgilabs vms
python -m esgilabs vms --pool jdupont
```

Colonnes : VM, VMID, Pool, Node, Status.

---

## `find` — Rechercher un étudiant

Retrouve un étudiant par son IP WAN, le nom de son VNet ou son nom d'utilisateur.
Affiche ses informations réseau et l'état live de sa VM sur Proxmox.

```bash
python -m esgilabs find 172.16.0.18      # par IP WAN
python -m esgilabs find vn00018          # par nom de VNet
python -m esgilabs find jdupont          # par nom d'utilisateur
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
python -m esgilabs credentials
```

> Les mots de passe sont affichés en clair — ne pas utiliser dans un contexte partagé.

---

## Options globales

| Option     | Description                                      |
|------------|--------------------------------------------------|
| `--help`   | Affiche l'aide (disponible sur chaque commande)  |
| `--yes, -y`| (apply uniquement) Pas de confirmation interactive |

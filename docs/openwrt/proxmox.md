# Interface Proxmox — votre espace étudiant

> **Audience** : étudiant ayant reçu des identifiants Proxmox.

Proxmox est l'hyperviseur du lab. Votre compte vous donne accès à votre pool
personnel et au pool de templates commun. Vous pouvez gérer vos VMs, en créer
de nouvelles depuis les templates, et consulter l'état de votre réseau VXLAN.

---

## Connexion

```
https://<proxmox-host>:8006
Utilisateur : jdupont@pve
Mot de passe : <fourni par l'administrateur>
```

> Changez votre mot de passe Proxmox à la première connexion :
> `Datacenter → My Account → Change Password`

---

## Votre pool personnel

Toutes vos ressources sont regroupées dans un **pool** portant votre nom (ex. `jdupont`).
Seules les ressources de votre pool vous sont visibles.

### Accéder à votre pool

```
Datacenter → pool → jdupont
```

Vous y trouvez :
- **Votre VM OpenWrt** (ex. `openwrt-jdupont`) — le routeur pré-configuré
- Toute VM ou LXC que vous créez dans votre pool

### Gérer votre VM OpenWrt

Depuis l'interface Proxmox, vous pouvez :
- **Démarrer / Arrêter** : onglet `Summary` → boutons `Start` / `Shutdown`
- **Console série** : onglet `Console` → console texte directe
- **Voir les métriques** : CPU, RAM, réseau en temps réel

---

## Pool template — templates disponibles

Le pool `template` contient les templates communes du lab, accessibles à tous
les étudiants en lecture.

```
Datacenter → pool → template
```

### Cloner une template dans votre pool

1. Sélectionner une template dans le pool `template`
2. Clic droit → `Clone`
3. Renseigner :
   - **VM ID** : un ID libre (ex. dans la plage `VMID_START + id + 100`)
   - **Name** : un nom descriptif
   - **Target Storage** : laisser le stockage par défaut
   - **Full Clone** : cocher (clone complet, indépendant de la template)
4. Cliquer `Clone`
5. Après la création, ajouter la VM à votre pool :
   `Clic droit → Move to pool → jdupont`

> Seuls les clones dans votre pool vous sont accessibles. Une VM hors pool ne
> sera pas visible depuis votre compte.

---

## Votre réseau VXLAN dans Proxmox

Votre VNet SDN est visible dans :

```
Datacenter → SDN → VNets → vn0XXXX (filtrer par zone)
```

Vous ne pouvez **pas modifier** la configuration du VNet (accès lecture seule via `PVESDNUser`).
En revanche, vous pouvez y connecter vos nouvelles VMs en sélectionnant votre VNet
comme bridge réseau lors de la création.

### Connecter une nouvelle VM à votre VXLAN

Lors de la création ou de la modification d'une VM :
```
Network → Bridge : vn0XXXX  (votre VNet personnel)
```

La VM recevra une adresse dans votre subnet `10.100.XX.0/24` (via DHCP si activé
sur votre OpenWrt, ou en IP statique).

---

## Créer un conteneur LXC

Les conteneurs LXC permettent de déployer rapidement des services Linux légers.

1. `Create CT` en haut à droite
2. Sélectionner le **template OS** souhaité (depuis le stockage partagé)
3. Configurer réseau → Bridge : `vn0XXXX`
4. Après création → déplacer dans votre pool : `Clic droit → Move to pool → jdupont`

---

## Limites de votre compte

| Action                          | Autorisé |
|---------------------------------|----------|
| Voir/gérer VMs de votre pool    | ✓        |
| Cloner les templates            | ✓        |
| Démarrer/arrêter vos VMs        | ✓        |
| Modifier la config réseau (VNet)| ✗        |
| Accéder aux pools des autres    | ✗        |
| Modifier les templates          | ✗        |
| Accéder à la configuration cluster | ✗     |

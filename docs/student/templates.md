# Utiliser les templates cloud-init

> **Audience** : étudiant — création de VMs Linux à partir des templates du pool `template`.

Les templates cloud-init permettent de démarrer rapidement une VM Linux pré-configurée
(Ubuntu, Debian, Fedora, Alpine…). Vous pouvez définir vos identifiants, votre réseau et vos
clés SSH directement depuis l'interface Proxmox.

---

## 1. Cloner une template

1. Aller dans **Datacenter → pool → template**
2. Sélectionner la template souhaitée (ex. `ubuntu-25.10`)
3. **Clic droit → Clone**
4. Renseigner :
   | Champ | Valeur recommandée |
   |---|---|
   | **VM ID** | Un ID libre dans votre plage (ex. `10200`) |
   | **Name** | Nom descriptif (`web-server`, `db01`…) |
   | **Pool** | le nomde votre pool (`jdupond`) |
   | **Target Storage** | Laisser le stockage par défaut |
   | **Mode** | **Full Clone** (clone complet, indépendant) |
5. Cliquer **Clone**

---

## 2. Connecter la VM à votre réseau VXLAN

Par défaut, le clone hérite du réseau de la template (bridge temporaire de build).
Il faut remplacer le bridge par votre VNet personnel.

1. **VM → onglet Hardware → Network Device (net0)**
2. Cliquer **Edit**
3. Changer **Bridge** par `vn0XXXXX` (vous pouvez voir que un seul vnet, le votre)
4. Valider

> Si votre VM a besoin d'accès à Internet, connectez-la au même VNet que votre OpenWrt.
> Le routeur OpenWrt fait le NAT vers le WAN automatiquement.

---

## 3. Configurer cloud-init

L'onglet **Cloud-Init** de la VM clonée permet de personnaliser la configuration avant le
premier démarrage. Les valeurs par défaut sont déjà renseignées par l'administrateur.

```
VM → onglet Cloud-Init
```

### Champs disponibles

| Champ | Description |
|---|---|
| **User** | Nom d'utilisateur du compte créé au boot |
| **Password** | Mot de passe du compte (haché dans l'image) |
| **SSH public key** | Clé(s) SSH autorisées pour se connecter sans mot de passe |
| **IP Config (net0)** | Configuration réseau (`DHCP` ou IP statique) |
| **DNS domain / servers** | Résolution DNS (optionnel) |

> Après chaque modification, cliquer **Regenerate Image** pour regénérer le drive cloud-init.

### Exemple — activer DHCP sur votre VNet

```
IP Config (net0) : ip=dhcp
```

Le routeur OpenWrt de votre lab distribuera une adresse dans votre subnet `10.100.XX.0/24`.


---

## 4. Démarrer la VM

1. **VM → Start** (bouton en haut à droite)
2. Ouvrir la **Console** pour suivre le boot
3. Cloud-init s'exécute automatiquement au premier démarrage :
   - Création du compte utilisateur
   - Application du mot de passe / clés SSH
   - Configuration réseau

Le premier boot peut prendre **30 à 90 secondes** selon l'image.

---

## 5. Se connecter en SSH

Vos VMs Linux sont dans votre réseau VXLAN privé (`10.100.XX.0/24`), non accessible
directement depuis le réseau du lab. Deux options pour y accéder en SSH :

### Option A — Rebond SSH via OpenWrt (recommandé)

Votre routeur OpenWrt est accessible depuis le réseau du lab et fait la passerelle vers
votre VXLAN. Consultez la doc [OpenWrt — SSH](../openwrt/base.md) pour configurer l'accès SSH sur
l'OpenWrt, puis utilisez le rebond :

```bash
# Connexion directe en une ligne via ProxyJump
ssh -J <user-openwrt>@<ip-wan-openwrt> <user>@<ip-vm>

# Exemple :
ssh -J root@172.16.0.18 ubuntu@10.100.12.45
```

Ou ajoutez un alias dans `~/.ssh/config` :

```
Host openwrt-lab
    HostName 172.16.0.18
    User root

Host ma-vm
    HostName 10.100.12.45
    User ubuntu
    ProxyJump openwrt-lab
```

Puis simplement :
```bash
ssh ma-vm
```

### Option B — Port forwarding NAT sur OpenWrt

Configurez une règle de redirection de port sur votre OpenWrt pour exposer le SSH de la VM :
consultez la doc [OpenWrt — NAT](../openwrt/nat.md).

---

L'IP de la VM est visible dans :
- La console série (affichée au boot)
- L'interface DHCP de votre OpenWrt : **LuCI → Status → DHCP leases**
- Proxmox → **VM → Summary** (si le guest agent est actif)

---

## 6. Référence — templates disponibles

| Template | OS | User par défaut | Notes |
|---|---|---|---|
| `ubuntu-25.10` | Ubuntu 25.10 | `labomatics` | guest agent inclus |
| `debian-13` | Debian 13 (Trixie) | `labomatics` | guest agent inclus |
| `fedora-43` | Fedora 43 | `labomatics` | guest agent inclus |
| `alpine-3` | Alpine 3.21 | `labomatics` | boot plus lent (~60s) |
| `opnsense-25` | OPNsense 25.1 | — | sans cloud-init (FreeBSD) |

> Le mot de passe par défaut est `changeme`
> à la première connexion.

---

## Dépannage

**La VM ne reçoit pas d'IP**
: Vérifier que le bridge est bien votre VNet (`vn0XXXXX`) et que votre OpenWrt est démarré.

**Connexion SSH refusée**
: Attendre la fin de cloud-init (30–90s). Vérifier que le mot de passe ou la clé SSH est
  correctement défini dans l'onglet Cloud-Init, puis régénérer l'image.

**La console affiche `cloud-init … failed`**
: Vérifier l'onglet Cloud-Init — un champ mal renseigné peut bloquer le boot.
  Supprimer le contenu du champ problématique et régénérer l'image.

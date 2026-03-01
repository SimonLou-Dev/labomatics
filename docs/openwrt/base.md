# Guide utilisateur — VM OpenWrt

> **Audience** : étudiant ayant reçu une VM OpenWrt dans le lab.

Votre VM est un routeur OpenWrt pré-configuré, cloné depuis une template commune.
Elle fait office de passerelle entre votre réseau personnel (LAN/VXLAN) et le
réseau du lab (WAN).

---

## Vos informations de connexion

L'administrateur vous a remis un document avec :

| Information              | Exemple           | Utilisation                          |
|--------------------------|-------------------|--------------------------------------|
| **IP WAN**               | `172.16.0.18`     | Adresse de votre VM depuis le lab    |
| **User Proxmox**         | `jdupont@pve`     | Connexion à l'interface Proxmox      |
| **Mot de passe Proxmox** | `Abc123XyzDef`    | Interface Proxmox                    |

---

## Réseau par défaut

Les adresses sont allouées de manière stable en fonction de votre identifiant étudiant.

| Interface | Rôle   | Adresse                         |
|-----------|--------|---------------------------------|
| `eth0`    | WAN    | IP WAN allouée (ex. `172.16.0.18/24`) |
| `eth1`    | LAN    | Gateway de votre subnet VXLAN (ex. `10.100.18.254/24`) |

**Subnet VXLAN (LAN)** : un `/24` alloué uniquement à vous. Toutes vos VMs
supplémentaires se connectent sur ce réseau.

| Élément           | Exemple (id=18)     |
|-------------------|---------------------|
| Subnet            | `10.100.18.0/24`    |
| Gateway (eth1)    | `10.100.18.254`     |
| VNet SDN          | `vn00018`           |
| WAN gateway       | `172.16.0.254`      |

---

## Accès à la VM

### Via SSH

```bash
ssh root@172.16.0.18       # Remplacez par votre IP WAN
# Mot de passe initial : openwrt
```

### Via LuCI (interface web OpenWrt)

```
https://172.16.0.18
```

Le certificat est auto-signé — acceptez l'exception de sécurité dans votre navigateur.

### Via l'interface Proxmox

Connectez-vous sur l'interface Proxmox avec vos identifiants :

```
https://<proxmox-host>:8006
Utilisateur : jdupont@pve
Mot de passe : <mot de passe fourni par l'administrateur>
```

Voir [proxmox.md](proxmox.md) pour utiliser Proxmox et accéder aux templates.

---

## Credentials par défaut de la VM OpenWrt

| Service | Utilisateur | Mot de passe |
|---------|-------------|--------------|
| SSH     | `root`      | `openwrt`    |
| LuCI    | `root`      | `openwrt`    |

> **Changez le mot de passe dès la première connexion :**
> ```bash
> passwd root
> ```

---

## Services actifs au démarrage

| Service          | Port(s) | Interface  |
|------------------|---------|------------|
| SSH (Dropbear)   | TCP 22  | WAN + LAN  |
| LuCI (uhttpd)    | TCP 443 | WAN + LAN  |
| qemu-guest-agent | —       | (interne)  |

---

## Réinitialiser la configuration réseau

Si la configuration réseau est corrompue, le script de configuration initiale
peut être relancé sans rebuild du template :

```bash
sh /etc/proxmox-init.sh
```

Cela réapplique : hostname, réseau depuis le drive cloud-init, uhttpd, et la règle
firewall WAN.

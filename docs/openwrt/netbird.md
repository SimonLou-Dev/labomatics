# Installer Netbird ou Tailscale sur votre routeur OpenWrt

> Vous n'avez pas besoin de faire cette manipulation pour joindre le routeur depuis le VPN/ZTNA de l'école, c'est déjà en place. Ce tuto sert uniquement si vous voulez, en plus, ajouter votre lab dans votre propre réseau Netbird ou Tailscale personnel.

Les deux sections sont indépendantes : choisissez Netbird **ou** Tailscale selon votre ZTNA, inutile d'installer les deux.

---

## Option A — Netbird

### 1. Installer le paquet

```bash
apk update
apk add netbird
```

### 2. Déclarer l'interface réseau

Netbird crée une interface WireGuard nommée `wt0`. Dans `/etc/config/network`, déclarez-la en `unmanaged` — Netbird gère lui-même l'adressage, OpenWrt n'a pas à lui attribuer d'IP :

```
config interface 'netbird'
        option device 'wt0'
        option proto 'none'
```

### 3. Ajouter la zone Netbird dans le firewall

Dans `/etc/config/firewall` :

```
config zone
        option name 'netbird'
        list network 'netbird'
        option input 'ACCEPT'
        option output 'ACCEPT'
        option forward 'REJECT'
        option masq '1'

config forwarding
        option src 'netbird'
        option dest 'lan'
```

- `forward REJECT` par défaut : seul le `forwarding` explicite netbird → lan ouvre un sens de trafic. Si vous avez aussi besoin de lan → netbird, ajoutez un second bloc `forwarding` symétrique — ne l'activez pas par défaut sans savoir pourquoi.
- `masq '1'` : si vous voulez propager tout le LAN du lab dans votre réseau Netbird (donc joindre n'importe quelle machine du lab depuis un peer Netbird, pas seulement le routeur), c'est la manière la plus simple d'y arriver. Sans masquerade, il faudrait annoncer la route du sous-réseau LAN côté Netbird (routes réseau dans le dashboard) et s'assurer que chaque peer sait router vers cette plage — plus propre mais plus de configuration. Avec masq, le routeur NAT tout le trafic lab → netbird derrière sa propre IP netbird : ça marche tout de suite, sans annonce de route, mais les peers distants ne voient plus l'IP réelle des machines du lab, seulement celle du routeur. Pour du debug ou du filtrage fin côté Netbird (limiter l'accès à une IP précise du lab), c'est une perte d'information. Pour un usage simple type "j'accède à mon lab depuis l'extérieur", c'est un compromis raisonnable.

### 4. Appliquer la configuration

```bash
uci commit network
uci commit firewall
/etc/init.d/network reload
/etc/init.d/firewall restart
```

### 5. Activer et démarrer le service au boot

```bash
/etc/init.d/netbird enable
/etc/init.d/netbird start
```

### 6. Se connecter à votre réseau Netbird

```bash
netbird up --setup-key <VOTRE_SETUP_KEY>
```

Si vous auto-hébergez votre propre serveur Netbird plutôt que le cloud officiel, ajoutez `--management-url` :

```bash
netbird up --setup-key <VOTRE_SETUP_KEY> --management-url https://netbird.example.com:443
```

Vérifiez la connexion :

```bash
netbird status -d
```

---

## Option B — Tailscale

### 1. Installer le paquet

```bash
apk update
apk add tailscale
```

### 2. Déclarer l'interface réseau

Tailscale crée une interface nommée `tailscale0`. Dans `/etc/config/network` :

```
config interface 'tailscale'
        option device 'tailscale0'
        option proto 'none'
```

### 3. Ajouter la zone Tailscale dans le firewall

Dans `/etc/config/firewall` :

```
config zone
        option name 'tailscale'
        list network 'tailscale'
        option input 'ACCEPT'
        option output 'ACCEPT'
        option forward 'REJECT'
        option masq '1'
        option mtu_fix '1'

config forwarding
        option src 'tailscale'
        option dest 'lan'
```

La documentation officielle recommande ici `masq` et `mtu_fix` activés par défaut sur la zone Tailscale, notamment si le routeur agit comme relais de sous-réseau (subnet router) vers le LAN.

### 4. Appliquer la configuration

```bash
uci commit network
uci commit firewall
/etc/init.d/network reload
/etc/init.d/firewall restart
```

### 5. Activer et démarrer le service au boot

```bash
/etc/init.d/tailscaled enable
/etc/init.d/tailscaled start
```

### 6. Se connecter à votre tailnet

Sans clé d'authentification, `tailscale up` génère un lien à ouvrir dans un navigateur pour vous authentifier via SSO :

```bash
tailscale up
```

Si vous préférez une authentification non interactive (clé pré-générée depuis la console d'admin Tailscale) :

```bash
tailscale up --authkey <VOTRE_AUTH_KEY>
```

Si vous voulez exposer les sous-réseaux LAN du routeur à tout le tailnet (subnet routing), ajoutez :

```bash
tailscale up --authkey <VOTRE_AUTH_KEY> --advertise-routes=192.168.1.0/24
```

Cette route devra ensuite être approuvée manuellement depuis la console d'admin Tailscale (elle n'est pas active par défaut, même après l'annonce).

Vérifiez la connexion :

```bash
tailscale status
```

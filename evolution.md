# Réflexions d'évolution — labomatics

> Notes d'architecture issues des discussions de conception.
> Ces fonctionnalités ne sont pas encore implémentées.

---

## 1. Gestion des professeurs

### Idée

Un `profs.csv` analogue à `students.csv` qui associe des profs à des classes.
Les profs reçoivent un accès lecture sur les pools des étudiants de leurs classes.

```csv
login,prenom,nom,classes
jmartin,Jean,Martin,"CO1,CO2"
adupont,Alice,Dupont,"CO2"
```

### Design retenu

- Rôle Proxmox : `PVEAuditor` sur chaque `/pool/{student_pool}` des étudiants des classes ciblées
- Lecture seule : voir console, CPU/RAM, snapshots — pas de modification ni démarrage
- ACLs appliquées **dans `student apply`** (pas une commande séparée) : si un étudiant CO2 est
  ajouté, tous les profs CO2 reçoivent automatiquement l'ACL sur son pool
- Le diff affiche les deux : étudiants à ajouter + ACLs profs impactées
- Changement de classes d'un prof → retrait des ACLs anciennes classes (même pattern que students)
- Pas de token API ni de pool dédié pour les profs — juste des ACLs sur les pools étudiants

### Intégration CLI

```
labomatics student apply   # gère étudiants + ACLs profs en une passe
labomatics student diff    # montre aussi le diff profs
```

---

## 2. Quotas natifs Proxmox

### Problème

`labomatics-quotad` est un daemon de polling externe (toutes les N secondes).
C'est réactif mais pas préventif — une VM peut tourner en surcharge 30 secondnes.

### Options analysées

#### Option A — ACL restrictives (recommandé en premier)

Créer un rôle `PVEVMStudent` sans `VM.Config.Memory`, `VM.Config.CPU`, `VM.Config.Disk`.
Les étudiants ne peuvent **physiquement pas** changer RAM/CPU/disk depuis l'UI ou l'API
avec leur token. Quota enforced au niveau auth, zéro overhead.

**À implémenter dans `set_student_acls()`** : remplacer `PVEVMAdmin` par `PVEVMStudent`.

#### Option B — Hookscript Proxmox

Chaque VM reçoit un paramètre `hookscript` pointant vers un snippet stocké dans Proxmox.
Le script est appelé en `pre-start` directement sur le nœud — si exit != 0, Proxmox
refuse le démarrage.

```bash
qm set <vmid> --hookscript local:snippets/labomatics-quota
```

Permet : détecter une config modifiée via token root, reset les valeurs, bloquer le start.

**Contrainte** : le script doit lire la config labomatics sur le nœud → couplage fort.
Sur un cluster, chaque nœud doit avoir le script et accès à `infra.yaml`.

#### Option C — quotad (existant)

Conservé comme filet de sécurité pour le disk I/O et les cas edge.
Moins pertinent si A + B sont en place.

### Recommandation

Combiner A (préventif, zéro coût) + B (défense en profondeur) + C (filet).

---

## 3. DNS étudiants

### Idée

`mkorniev.esgi.local` → IP WAN de l'OpenWrt de l'étudiant  
`mkorniev-srv1.esgi.local` → IP d'une VM TP de l'étudiant

Résolution depuis le réseau du lab sans connaître les IPs.

### Options

**Simple** : `dnsmasq` sur pve1, `student apply` régénère un fichier de config statique.

```
address=/mkorniev.esgi.local/172.16.0.19
address=/mkorniev-srv1.esgi.local/10.100.5.1
```

**Robuste** : PowerDNS avec backend SQLite + API REST. `labomatics` appelle l'API PowerDNS
à chaque apply/undeploy pour les updates dynamiques.

```bash
curl -X PATCH http://localhost:8053/api/v1/servers/localhost/zones/esgi.local \
  -d '{"rrsets": [{"name": "mkorniev.esgi.local.", "type": "A", ...}]}'
```

**Indépendant de l'UI** — peut être implémenté à n'importe quel stade.

---

## 4. Interface utilisateur

### Options analysées (du plus simple au plus complexe)

#### Option A — TUI Textual (court terme)

Menu interactif dans le terminal (Python `textual`). Aucune infrastructure nouvelle.
Idéal pour la gestion des classes, étudiants, profs sans quitter le terminal.

- ✓ Zéro serveur, zéro DB
- ✓ 1-2 semaines de dev
- ✗ Pas accessible depuis un navigateur

#### Option B — FastAPI + SQLite mono-nœud (moyen terme)

Un process FastAPI sur pve1, UI web (HTMX ou React léger). Remplace les CSV par SQLite.

```
navigateur → https://pve1:8080
                    ↓
              FastAPI (pve1)
              ├── SQLite (students, profs, classes, deploy history)
              └── proxmoxer → API Proxmox
```

**Le bon palier pour un lab** : 80% des bénéfices, 20% de la complexité.

- ✓ Accès navigateur multi-utilisateur
- ✓ Historique des actions, logs
- ✓ 3-4 semaines de dev
- ✗ Single point of failure (pve1)

#### Option C — Mode serveur distribué (long terme)

FastAPI + PostgreSQL (Patroni) + Redis Sentinel sur chaque nœud.

```
pve1: FastAPI + PostgreSQL (primary) + Redis
pve2: FastAPI + PostgreSQL (replica) + Redis
pve3: FastAPI + PostgreSQL (replica) + Redis
```

**Réservé aux besoins multi-sites ou SaaS.** Overkill pour un cluster de 4 nœuds de lab.
Complexité : élection master DB, lock distribué pour les apply Proxmox, déploiement multi-nœuds.

---

## 5. Intégration dans l'UI Proxmox

### Système de plugins officiel (PVE ≥ 7.4)

Proxmox accepte des packages Debian qui ajoutent des composants ExtJS à l'interface.
Fichiers déposés dans `/usr/share/pve-manager/ext6/pvemanagerlib.js`.

### Approche retenue : plugin iframe

```
Proxmox UI
└── Datacenter > Onglet "Labomatics" (plugin JS ~50 lignes)
    └── <iframe src="https://pve1:8080">
                └── FastAPI + HTMX (Option B)
```

Crée un package `labomatics-pve-plugin` installé avec `dpkg -i` sur chaque nœud.
L'admin voit tout dans Proxmox sans ouvrir un autre onglet.

- ✓ "Dans" Proxmox visuellement
- ✓ 2-3 jours de dev (plugin) + Option B (app)
- ✗ Pas visuellement natif (ExtJS)

### Approche alternative : plugin ExtJS natif

Vrais composants ExtJS, même look & feel que Proxmox. Grilles, boutons, formulaires natifs.
Développement 3-4 semaines. ExtJS est verbeux et peu documenté.

**Réservé à une contribution upstream ou un produit commercial.**

---

## 6. Module CTF on-demand

### Idée

Plateforme CTF entièrement on-demand sur Proxmox : les instances de challenge sont créées
à la demande par équipe/joueur et détruites après résolution ou timeout.

### Architecture

```
CTFd (frontend)          ← gestion teams, flags, scoreboard
    ↓ webhook / API
Orchestrateur FastAPI    ← routage selon le type de challenge
    ├── Docker API       ← challenges légers (web, crypto, pwn)
    └── proxmoxer        ← challenges lourds (AD, réseau, forensics OS)
```

Chaque challenge embarque dans ses métadonnées : `backend: docker|proxmox`,
`template: <nom>`, `timeout: 3600`, `network: isolated|wan`.

### Backends

**Docker** (challenges légers) :
- Spawn rapide (< 5s), faible overhead
- Isolation par network Docker par instance
- Adapté : web, crypto, pwn, reverse, misc

**Proxmox** (challenges lourds) :
- Clone de template QEMU/LXC par instance
- Isolation réseau via SDN VXLAN (même mécanisme que les TPs étudiants)
- Adapté : Active Directory, forensics OS, challenges réseau complets, pivoting

### Points critiques

**Exposition réseau** :
Traefik en reverse proxy dynamique — chaque instance reçoit un sous-domaine ou un port
unique généré à la création, Traefik est notifié via son API ou via labels Docker/tags Proxmox.

```
team42-web01.ctf.esgi.local → instance Docker team42
team42-ad01.ctf.esgi.local  → VM Proxmox team42
```

**Garbage collection** :
Daemon de GC qui poll les instances actives et détruit celles dont le timeout est dépassé
ou dont le challenge a été résolu. Sans GC, les ressources Proxmox saturent rapidement
sur un CTF de plusieurs heures avec beaucoup d'équipes.

```python
# Cycle GC (toutes les 60s)
for instance in active_instances:
    if instance.solved or time.now() > instance.expires_at:
        destroy(instance)   # Docker rm / proxmox delete
        deregister_traefik(instance)
```

**Flags dynamiques** :
Chaque instance reçoit un flag unique (`FLAG{sha256(team_id + challenge_id + secret)[:16]}`)
injecté au spawn via cloud-init (Proxmox) ou variable d'environnement (Docker).
CTFd valide le flag via webhook POST vers l'orchestrateur, qui confirme team + challenge.

### Intégration avec labomatics

- Réutilise `find_vm_node()`, `pick_node()`, `wait_for_task()` du module `proxmox/`
- Templates CTF gérées par `template build` (même pipeline que les templates TP)
- SDN VXLAN par instance : même mécanisme que les VNets étudiants
- Pool Proxmox dédié `ctf-instances` avec quotas stricts (GC en dernier recours)

### Roadmap CTF

```
Étape 1 — Orchestrateur minimal
├── FastAPI : POST /spawn {challenge_id, team_id} → {host, port, flag, expires_at}
├── DELETE /instance/{id}
├── Backend Docker uniquement
└── GC simple (cron toutes les 60s)

Étape 2 — Backend Proxmox
├── Clone template QEMU/LXC par instance
├── Injection flag cloud-init
└── SDN VXLAN isolé par instance

Étape 3 — Exposition & intégration CTFd
├── Traefik dynamique (labels ou API)
├── Webhook CTFd → validation flag dynamique
└── Dashboard admin (instances actives, ressources consommées)
```

---

## Roadmap suggérée

```
Phase 1 (court terme)
├── profs.csv + ACLs lecture classes             [2-3 jours]
├── Rôle PVEVMStudent (quotas ACL)               [1 jour]
└── DNS dnsmasq intégré dans apply               [1 jour]

Phase 2 (moyen terme)
├── FastAPI + SQLite (remplace CSV)              [3-4 semaines]
├── Plugin Proxmox iframe                        [2-3 jours]
└── Module CTF — orchestrateur + backend Docker  [2-3 semaines]

Phase 3 (si besoin)
├── Hookscript quota Proxmox                     [1 semaine]
├── PowerDNS dynamique                           [1 semaine]
└── Module CTF — backend Proxmox + Traefik       [2-3 semaines]
```

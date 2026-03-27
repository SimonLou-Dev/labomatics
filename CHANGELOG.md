# CHANGELOG


## v0.3.0 (2026-03-27)

### Bug Fixes

- **setup**: Wizard idempotent + retry loop étape 6 + stockage single-node
  ([`939c469`](https://github.com/SimonLou-Dev/labomatics/commit/939c469204400bbf19e89897f8a861b62c972704))

- ne plus écraser .env/infra.yaml/students.csv déjà présents (vérif par fichier) - _verify_config
  retourne bool : la boucle reboucle si storage/bridge/zone SDN absent - étape 4 single-node : liste
  les stockages disponibles au lieu d'ignorer - template openwrt : corriger le message "lancez plus
  tard"

### Documentation

- Mettre à jour la référence CLI avec la nouvelle structure par groupes
  ([`4c0bbcf`](https://github.com/SimonLou-Dev/labomatics/commit/4c0bbcf203b5fde1f03d9c44ec26dbb048dac3f0))

- **readme**: Mettre à jour les commandes CLI (nouvelle structure par groupes)
  ([`df31c02`](https://github.com/SimonLou-Dev/labomatics/commit/df31c02892874e7079a3366eb7ba1a9dc3dacd55))

### Features

- **deploy**: Pipeline TP complet + CLI tp group + workers automatiques
  ([`1be3df6`](https://github.com/SimonLou-Dev/labomatics/commit/1be3df6c9e42e002bb90dfb3e60f6895915ba98f))

CLI : - Nouveau groupe `tp` (deploy / undeploy) séparé de `student` - Suppression de --workers :
  parallélisme automatique (1 thread/VM) - Groupe `network` (zones/vnets/ips), `template openwrt`

deploy.py : - _vmid_lock couvre nextid() + clone POST : élimine les races VMID - Tags Proxmox
  sanitisés (labomatics-tp--{name}, sans caractères invalides) - Cloud-init drive : pas de
  recréation si déjà présent dans le clone - Disk resize : détection automatique du disque de boot
  (pas de scsi0 hardcodé) - Nettoyage post-clone en cas d'échec (stop + delete purge) - Rich
  Progress : une ligne spinner par (étudiant × VM), résultat in-place

students.py / _helpers.py : - Warning si colonne `classe` absente du CSV - pick_node() dispatch sur
  le nœud le plus disponible en mémoire

proxmox/vms.py : - find_tp_vms : tag labomatics-tp--{name} (double tiret, sans deux-points)


## v0.2.0 (2026-03-08)

### Bug Fixes

- Build & téléchargement de la template
  ([`09a04fb`](https://github.com/SimonLou-Dev/labomatics/commit/09a04fb16c1571ca3c3113c38a2bef350494e275))

- **apply**: Éviter doublons subnet VXLAN dans un batch multi-étudiants
  ([`08386f1`](https://github.com/SimonLou-Dev/labomatics/commit/08386f1b7388ba7a6217b5de2b08265c3a99793f))

- ip_pool: allocate_vxlan_subnet accepte un set 'reserved' pour éviter les collisions intra-batch
  (subnets non encore visibles dans Proxmox) - apply: accumule reserved_vxlan pendant la boucle de
  création - credentials: rétrocompatibilité lecture ancien format CSV (sans colonne login) -
  build_openwrt: wget direct + gzip exit 2 non fatal + pool template auto-créé - build_openwrt:
  renommage variable f → pfile (conflit mypy)

- **build-openwrt**: Lire disk_id depuis qm config après importdisk
  ([`b7ea8c8`](https://github.com/SimonLou-Dev/labomatics/commit/b7ea8c8534b3a35225a04bb473d69c287e7a65d2))

- **build-openwrt**: Lire storage et vmid depuis infra.yaml, CLI surcharge
  ([`296438a`](https://github.com/SimonLou-Dev/labomatics/commit/296438a888a9742ea9e9337ce1443c442ed4dd44))

- **build-template**: Corriger Alpine premier boot + pipeline templates
  ([`8a24bd7`](https://github.com/SimonLou-Dev/labomatics/commit/8a24bd7204d08107eef3e703b7c671dd8e7ed319))

- virt-customize : rc-update → symlink direct /etc/runlevels/default (rc-update échoue en chroot
  guestfs sans /run/openrc/softlevel) - virt-customize : supprimer cc_reset_rmc de cloud.cfg (bloque
  le premier boot Alpine sur VM sans BMC) - pipeline : reset VM + nouvel essai si timeout guest
  agent (OpenRC ne démarre pas le GA au premier boot, OK après reset) - config : default_packages
  (global) + extra_packages (par template) + download_packages flag + cpu_type + boot_timeout par
  template - infra.yaml.example : iso_filename pour Ubuntu/OPNsense, Alpine kvm64 - docs : guide
  étudiant templates cloud-init, référence YAML admin

- **deploy**: Fallback clone sur nœud source si stockage local
  ([`ed8eae7`](https://github.com/SimonLou-Dev/labomatics/commit/ed8eae77d0341f943bd8229ff8c005e5122796d3))

- **destroy**: Stocker vnet dans le commentaire du pool + supprimer VNet et LXC à la suppression
  ([`ae1b5e5`](https://github.com/SimonLou-Dev/labomatics/commit/ae1b5e5384b4dcbb56d1edb9bac3a094bbda7862))

- **quotas**: Supprimer set_pool_limits — max_cpu/ram/disk inexistants dans l'API Proxmox
  ([`ab97fe1`](https://github.com/SimonLou-Dev/labomatics/commit/ab97fe18fc630c6aa288679b3f742189c032af96))

### Chores

- Ajuster config réseau lab + supprimer ancien script shell build-openwrt
  ([`870a652`](https://github.com/SimonLou-Dev/labomatics/commit/870a65282f6db7f4733739941d399550c36933b7))

### Continuous Integration

- **release**: Sync dev sur main après chaque release
  ([`6f35ed9`](https://github.com/SimonLou-Dev/labomatics/commit/6f35ed91ee61181e118ecb166bfdfcbb2ee38f98))

- **release**: Sync dev sur main après chaque release
  ([`3c6aac7`](https://github.com/SimonLou-Dev/labomatics/commit/3c6aac70a44c3abf13b5a4632d2bb785a63c9656))

### Documentation

- Ajouter guide Terraform bpg/proxmox pour les étudiants
  ([`a838c9f`](https://github.com/SimonLou-Dev/labomatics/commit/a838c9f2b4703ae9555e81778d25a5c57fab0b1e))

- Mettre à jour install Python, build-openwrt, CLI, SSH+NAT OpenWrt
  ([`9c72168`](https://github.com/SimonLou-Dev/labomatics/commit/9c721682e110ca3c1aca4f2f64d874eec6f8ca7b))

### Features

- Ajout d'un diagramme d'architecture
  ([`f6439fa`](https://github.com/SimonLou-Dev/labomatics/commit/f6439faa8b23c2d7fb58e07164fee6150eb6dd8b))

- Ajout d'un diagramme d'architecture
  ([`94c8b5e`](https://github.com/SimonLou-Dev/labomatics/commit/94c8b5e5be3d994c9629f1fd9a2c341c6a2c35fd))

- Deploy/undeploy TP + filtre --classe par groupe d'étudiants
  ([`c5e7238`](https://github.com/SimonLou-Dev/labomatics/commit/c5e7238a741d43df14dac86777627909365f438e))

- students.py : champ `classe` optionnel (rétrocompat CSV sans colonne) - config.py : modèles
  TpConfig/TpVmConfig/TpNicConfig/TpCloudInitConfig + load_tp_config() - proxmox/vms.py :
  find_tp_vms() (tag labomatics-tp:), get_vm_description() - commands/deploy.py : cmd_deploy +
  cmd_undeploy · net0 = VNet VXLAN étudiant (toujours) ; extra_nics optionnels · cloud-init
  user/password + dhcp optionnel · idempotence via config_hash dans la description VM · parallélisme
  ThreadPoolExecutor (--workers, défaut 2) · undeploy par fichier (-f) ou par nom (--tp) -
  apply/diff/status/find/credentials : filtre --classe

- Permettre à la commande 'apply --recheck-all' de prendre en charge les anciennes versions de
  credential.cvs
  ([`4ff8fe4`](https://github.com/SimonLou-Dev/labomatics/commit/4ff8fe440ebb2b905cf6ad29062724f7d7150897))

- **apply**: Token API par étudiant + apply --recheck-all
  ([`86dbc58`](https://github.com/SimonLou-Dev/labomatics/commit/86dbc58da8818e81b237a03f5a6fe0349785b09e))

- **build-openwrt**: Externaliser OPENWRT_INIT + masquerade WAN + SSH ouvert depuis WAN
  ([`7cbc5b8`](https://github.com/SimonLou-Dev/labomatics/commit/7cbc5b8103ad753cef4dfe34115eaab127940d2f))

- **build-openwrt**: Récupérer la dernière version OpenWrt automatiquement
  ([`9852590`](https://github.com/SimonLou-Dev/labomatics/commit/985259057466eb687ed858cef198f1110fd99021))

- **build-template**: Passer les variables Proxmox via -var packer + TemplateConfig enrichi
  ([`881d2ad`](https://github.com/SimonLou-Dev/labomatics/commit/881d2ad14a5c69d6929da20782aef72912689d4b))

- **package**: Templating packer
  ([`fcc359d`](https://github.com/SimonLou-Dev/labomatics/commit/fcc359daa41a92fce4eae6b805d94f1661106b6f))

- inclure labomatics/packer/ dans le wheel - ajout des tempalte ubuntu, alpine, fedora - rework du
  infra.yaml - lanceur packer

### Refactoring

- Cli docker-style (groupes) + wizard setup interactif
  ([`e7323ec`](https://github.com/SimonLou-Dev/labomatics/commit/e7323ec7e0f20bb0462e6c79f600cd19c3547c1c))

Nouvelle structure CLI : labomatics setup labomatics student
  apply/diff/list/status/find/creds/recreate/deploy/undeploy/destroy labomatics pool list/ips
  labomatics sdn zones/vnets labomatics template build/build-openwrt

Wizard setup (commands/setup.py) : - Saisie interactive credentials Proxmox → .env - Copie templates
  infra.yaml + students.csv - Vérification connexion Proxmox + liste nœuds - Détection stockage
  partagé (multi-nœuds) - Ouverture éditeur (vim/nano/$EDITOR) sur infra.yaml - Vérifications
  bridges, storages, zone SDN - Création pool template - Conseil SPICE - Proposition build template
  OpenWrt


## v0.1.1 (2026-03-05)

### Bug Fixes

- **urls**: Corriger les URLs vers labomatics (sans r)
  ([`e0216b6`](https://github.com/SimonLou-Dev/labomatics/commit/e0216b6d4a7ebaae2aa47922c27d84ce2bf5dff5))

### Documentation

- **links**: Correction des liens vers la documentation
  ([`2cf32d0`](https://github.com/SimonLou-Dev/labomatics/commit/2cf32d0d64fc4782585c31558542ea13e1660620))


## v0.1.0 (2026-03-05)

### Bug Fixes

- **config**: Corriger les URLs vers le bon repo (SimonLou-Dev/labomatrics)
  ([`4feb818`](https://github.com/SimonLou-Dev/labomatics/commit/4feb818e270ef5e3be8cc93a55f7a0682d5799d6))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **lint**: Corriger toutes les erreurs mypy (no-any-return, type unions IPv4/IPv6)
  ([`16440a6`](https://github.com/SimonLou-Dev/labomatics/commit/16440a62ebb8b347951b72a430bf501e71fce4bf))

- proxmox/vms.py : cast str() sur les retours Any de dict.get("node") - config.py : type:
  ignore[call-arg] sur ProxmoxSettings() (pydantic-settings) - ip_pool.py : remplacer ip_network()
  par IPv4Network() pour éviter les unions IPv4|IPv6 - daemon/quotad.py : guard None sur node avant
  wait_for_task

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- **deps**: Ajouter mkdocs-material dans les deps de dev
  ([`bff5493`](https://github.com/SimonLou-Dev/labomatics/commit/bff549373fefdf7aa26f75950efe087e37479b33))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Code Style

- Ruff format
  ([`924420d`](https://github.com/SimonLou-Dev/labomatics/commit/924420deb2e3f4bed0cefc50eb326f6905e23b7d))

- Ruff format (formatage automatique)
  ([`006a619`](https://github.com/SimonLou-Dev/labomatics/commit/006a619a84adbf5a23594b0532fd7493363b42f0))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Continuous Integration

- **docs**: Workflow GitHub Pages avec MkDocs Material
  ([`1b07438`](https://github.com/SimonLou-Dev/labomatics/commit/1b0743828b1b20af7915e64133decfe8f170300c))

Déploie automatiquement la documentation sur gh-pages à chaque push sur main qui modifie docs/ ou
  mkdocs.yml.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **release**: Utiliser PAT_SEMANTIC_RELEASE pour bypass branch protection
  ([`60617a7`](https://github.com/SimonLou-Dev/labomatics/commit/60617a70663ea37faa25e3d175c8b6590bd69b7a))

GITHUB_TOKEN ne peut pas bypasser les rulesets sur les repos personnels. Un PAT (Fine-grained,
  contents: write) est requis pour que semantic-release puisse pusher le commit de version bump sur
  main protégé.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- **readme**: Badge PyPI + liens absolus compatibles PyPI
  ([`751bf6c`](https://github.com/SimonLou-Dev/labomatics/commit/751bf6c2aae6e1f58244187dddbe2c3ad5aff93f))

Les liens relatifs (docs/admin/, LICENSE) ne fonctionnent pas sur la page PyPI — remplacés par des
  URLs absolues GitHub/GitHub Pages. Ajout des pastilles PyPI, Python version, licence et docs.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **setup**: Venv Proxmox Debian, étape init, build-openwrt, format CSV
  ([`549e05c`](https://github.com/SimonLou-Dev/labomatics/commit/549e05c54da88bb0a472a0b20800a9bdaed81676))

- Installation via venv (/opt/labomatics) pour Proxmox Debian - Étape 4 : labomatics init avant le
  premier apply (étape 5) - Référence labomatics build-openwrt au lieu du shell script - Format
  students.csv : nom/prenom séparés, login calculé automatiquement - credentials.csv : nouvelle
  colonne login + nom complet

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Refactoring complet esgilabs → labomatics
  ([`ba105f3`](https://github.com/SimonLou-Dev/labomatics/commit/ba105f38773609ead04b42c73dc277c13450a2d9))

Renommage du package et refactoring complet en package pip installable.

- Nouveau package `labomatics` avec entry points `labomatics` et `labomatics-quotad` - Allocation IP
  dynamique depuis Proxmox (WAN/VXLAN), sans fichier d'état local - Flavors : profils CPU/RAM/disk
  par étudiant (infra.yaml) - Quotas natifs Proxmox via set_pool_limits() + daemon labomatics-quotad
  - Nouvelles commandes : ips, status, recreate, build-template, init - Pipeline build-template :
  Packer + provisioning SSH/guest-agent - pyproject.toml (hatchling) + semantic-release + CI/CD
  GitHub Actions - 22 tests unitaires (config, students, ip_pool) - students.csv : nouvelles
  colonnes prenom et flavor - infra.yaml v2 : wan_pool/vxlan_pool avec exclusions, flavors, quotad,
  templates

- **cli**: Ajouter commande destroy-all
  ([`59f1782`](https://github.com/SimonLou-Dev/labomatics/commit/59f17826e432cfe02c64b1287fa2de585ef97f3c))

Supprime toutes les ressources étudiants gérées (VMs, VNets, ACL, utilisateurs, pools). Équivaut à
  un apply avec CSV vide. Usage : labomatics destroy-all [--yes]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Remplacer le shell script par labomatics build-openwrt
  ([`89f28b3`](https://github.com/SimonLou-Dev/labomatics/commit/89f28b3b62d748e7bdb7d05832ad879e641a557d))

Migration de scripts/build-openwrt-vm-template.sh vers une commande Python. Même fonctionnalité :
  download image, montage losetup, injection mot de passe/SSH/HTTPS/qemu-ga/uci-defaults, création
  template Proxmox. Doit être exécuté en root sur le nœud Proxmox. Usage : labomatics build-openwrt
  [--version] [--vmid] [--storage] [--password]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **docs**: Ajouter mkdocs.yml + page d'accueil
  ([`df058a6`](https://github.com/SimonLou-Dev/labomatics/commit/df058a629486bd9013ac165bd689715d55b4da11))

Config MkDocs Material avec navigation en onglets (Admin / OpenWrt). Page d'accueil docs/index.md
  avec résumé et liens vers les sections.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **students**: Login = première lettre prénom + nom en minuscule
  ([`4160d8a`](https://github.com/SimonLou-Dev/labomatics/commit/4160d8a551d8c4d2e8728b6eeb9bd217bf527bbd))

Student.login() calcule l'identifiant Proxmox automatiquement depuis prenom+nom du CSV. Mise à jour
  de pool_name(), user_id(), vm_name() et credentials (clé "login" + champ "nom" = prénom + nom
  complet).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Refactoring

- **lint**: Nettoyage imports et variables inutilisés
  ([`fad56fd`](https://github.com/SimonLou-Dev/labomatics/commit/fad56fd34ca647f42efef6d39fa7dabc670b3456))

Corrections ruff restantes : réordonnancement des imports (isort), suppression d'imports et
  variables non utilisés.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

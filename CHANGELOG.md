# CHANGELOG


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

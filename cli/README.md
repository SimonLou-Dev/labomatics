# labomatics CLI v0.4

Orchestration centrale pour déployer la stack labomatics sur Proxmox.

## Installation

```bash
cd cli/
pip install -e .
```

## Utilisation

### `labomatics install`

Initialiser le cluster (créer VM centrale + stack Docker).

**À exécuter sur un nœud du cluster Proxmox.**

```bash
labomatics install [--dry-run] [--hostname NAME] [--domain DOMAIN] [--storage STORAGE]
```

Demande interactivement:
- URL Proxmox
- User + Token API (admin complet)
- Configuration de la VM

Services déployés (Docker Compose):
- PostgreSQL
- Keycloak (SSO)
- FreeRADIUS (authentification réseau)
- DNS (dnsmasq)
- Traefik (reverse proxy)

À terme: API + Frontend

## Security Note

Le token Proxmox est admin complet. Recommandation: créer un token dédié avec un compte limité (voir docs/).

## Architecture

```
cli/
├── labomatics_cli/
│   ├── __main__.py              # Entry point, argparse
│   ├── commands/
│   │   └── install.py           # Commande install
│   ├── utils/
│   │   ├── proxmox.py           # Client Proxmox
│   │   └── config.py            # Gestion config
│   └── provisioning/
│       └── templates/
│           └── cloud-init.sh    # Script Alpine + Docker
└── pyproject.toml
```

## Status

- [ ] `labomatics install` — scaffold
- [ ] Proxmox API client
- [ ] VM creation (Alpine template)
- [ ] Cloud-init injection
- [ ] HA configuration
- [ ] Service validation

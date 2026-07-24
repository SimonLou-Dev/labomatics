# labomatics CLI v0.4

Orchestration centrale pour déployer le cluster labomatics sur Proxmox.

## Installation

```bash
cd cli/
pip install -e .
```

## Utilisation

### `labomatics install`

Initialiser le cluster central (VM Alpine + Docker stack).

**À exécuter sur un nœud du cluster Proxmox.**

```bash
labomatics install [--dry-run]
```

### Flow interactif

1. **Configuration**: domaine root, interface réseau
2. **VM**: user, password, IP, gateway
3. **Passwords**: générés automatiquement
4. **Compte admin**: email, nom, prénom
5. **Installation**: VM → Docker → Services → Keycloak setup
6. **Output**: credentials + OIDC setup pour Proxmox

### Services déployés

- **PostgreSQL**: 3 DBs (labomatics, keycloak, powerdns)
- **Keycloak**: SSO (realms: master + labomatics)
- **PowerDNS**: DNS server (API REST)
- **Traefik**: Reverse proxy

## Architecture

```
cli/
├── labomatics_cli/
│   ├── __main__.py
│   ├── commands/
│   │   └── install.py         # Commande install complète
│   └── utils/
│       ├── ssh.py             # Client SSH
│       ├── keycloak.py        # API Keycloak
│       ├── powerdns.py        # API PowerDNS
│       └── proxmox.py         # API Proxmox (stub)
└── pyproject.toml

provisioning/labomatics/
├── templates/
│   ├── cloud-init.sh          # Cloud-init minimal
│   ├── docker-compose.yml     # Stack Docker
│   ├── traefik.yaml           # Config Traefik
│   └── powerdns.conf          # Config PowerDNS
└── scripts/
    ├── init-databases.sh      # Init PostgreSQL DBs
    └── setup-docker.sh        # Setup Docker (SSH)
```

## Security Notes

- Passwords générés par cryptographie forte
- Keycloak master realm: admin générés, utilisés uniquement par le CLI
- Labomatics realm: admin = user créé (email/nom/prénom)
- Certificats self-signed (à améliorer avec Let's Encrypt)

## Status

- [x] Structure et scaffolding
- [x] Cloud-init Proxmox-compatible
- [x] Docker Compose (PostgreSQL, Keycloak, PowerDNS, Traefik)
- [x] Commande install (flow complet)
- [x] Setup Keycloak realms + user admin
- [x] OIDC client pour Proxmox
- [ ] Proxmox API client (VM creation)
- [ ] SSH file upload/exec (Paramiko)
- [ ] Tests
- [ ] Idempotence

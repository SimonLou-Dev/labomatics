# labomatics CLI v0.4

Orchestration centrale pour déployer le cluster labomatics sur Proxmox.

## Installation

```bash
cd cli/
pip install -e .
```

## Utilisation

### `labomatics install`

Installe la stack Labomatics (VM, Docker, Keycloak, backend, agent) sur un cluster Proxmox.
Le CLI s'exécute en local et pilote Proxmox par API et SSH.

```bash
labomatics install [--cluster NOM]
```

#### Wizard

Un assistant interactif pose les questions en 10 pages : Proxmox, VM Labomatics,
Labs WAN, Labs VXLAN, compte d'administration, authentification, fédération LDAP externe,
reverse proxy, e-mail, accès SSH aux nœuds (un mot de passe par nœud). Un récapitulatif
précède l'installation, qui enchaîne 13 tâches (token, zone VXLAN, VM, Docker, DNS,
stack, Keycloak, client OIDC Proxmox, backend, agent, contrôle de santé).
Chaque page et chaque tâche est sauvegardée à la volée. À la fin, l'écran affiche
les URLs, l'identifiant administrateur et son mot de passe temporaire.

#### Reprise et mode édition

Tout est stocké dans `~/.labomatics/clusters/<cluster>/` (`install.yaml` et `state.json`,
droits 600). Sans `--cluster`, le wizard propose les clusters existants ou un nouveau.

- **Reprise** : installation interrompue, le wizard reprend à la première page non
  sauvegardée et les tâches déjà terminées sont ignorées.
- **Édition** : installation terminée, les valeurs déjà enregistrées sont verrouillées
  (on peut ajouter des éléments aux listes) et seules les tâches concernées par les
  changements sont rejouées.

### Services déployés

- **PostgreSQL** : bases labomatics et keycloak
- **Keycloak** : SSO (realms master et labomatics)
- **OpenLDAP / FreeRADIUS** : annuaire et authentification réseau
- **dnsmasq** : DNS de la VM
- **Traefik** : reverse proxy
- **Backend FastAPI et frontend**

## Architecture

```
cli/
├── labomatics_cli/
│   ├── __main__.py
│   ├── installer/        # App, pages du wizard, tâches, store, clients Proxmox/Keycloak/SSH
│   ├── tui/              # Kit prompt_toolkit (wizard, champs, validateurs)
│   ├── models/           # InstallConfig (config d'installation)
│   ├── templates/        # Templates Jinja2 de la VM (dns, ldap, radius, stack, traefik)
│   ├── commands/         # `labomatics template`
│   └── utils/            # Utilitaires de `labomatics template`
└── pyproject.toml
```

## Security Notes

- Passwords générés par cryptographie forte
- Keycloak master realm: admin générés, utilisés uniquement par le CLI
- Labomatics realm: admin = user créé (email/nom/prénom)
- Certificats self-signed (à améliorer avec Let's Encrypt)

## Status

- [x] Structure et scaffolding
- [x] Docker Compose (PostgreSQL, Keycloak, LDAP, Traefik)
- [x] Commande install (wizard, reprise, mode édition)
- [x] Setup Keycloak realms + user admin
- [x] OIDC client pour Proxmox
- [x] Client Proxmox, SSH (Paramiko), tests
- [x] Idempotence (reprise par tâche)

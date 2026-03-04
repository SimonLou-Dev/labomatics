# Changelog

Généré automatiquement par [python-semantic-release](https://python-semantic-release.readthedocs.io/).

<!-- Les entrées ci-dessous sont ajoutées automatiquement lors de chaque release. -->

## v0.1.0 (2025-03-04)

### Features

- Initial release — refactoring complet d'esgilabs en package pip installable
- Allocation IP dynamique depuis Proxmox (WAN et VXLAN), sans fichier d'état local
- Flavors : profils CPU/RAM/disk par étudiant définis dans infra.yaml
- Quotas natifs Proxmox via `set_pool_limits()` (max_cpu/ram/disk)
- Daemon `labomatics-quotad` : surveillance des quotas, arrêt de la VM la plus gourmande
- Commande `ips` : % d'utilisation des pools WAN et VXLAN
- Commande `status` : ressources CPU/RAM/disk par étudiant vs flavor
- Commande `recreate` : destroy + redeploy d'un étudiant
- Commande `build-template` : pipeline Packer + provisioning SSH/guest-agent
- Commande `init` : création de /etc/labomatics/ avec les configs par défaut
- Nouveau format infra.yaml v2 : wan_pool/vxlan_pool avec exclusions, flavors, quotad, templates
- students.csv : nouvelles colonnes prenom et flavor

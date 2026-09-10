# CHANGELOG


## v0.4.0-rc.10 (2026-09-10)

### Bug Fixes

- Import types directly from submodules
  ([`d36ea24`](https://github.com/SimonLou-Dev/labomatics/commit/d36ea24720658a23fddb46c8161b48e8b493bd8a))

- Remove unused delete_by_vmid method
  ([`417eb0c`](https://github.com/SimonLou-Dev/labomatics/commit/417eb0c09e1e4a814950f3654feaec40f42901fe))

- Typescript - remove duplicate types, handle null exclusions
  ([`1b887c7`](https://github.com/SimonLou-Dev/labomatics/commit/1b887c7cdd8acf4b6084f671135eaedde093ff29))

- Typescript types - add proxmox_url, remove duplicate LabDataDTO, add createLab
  ([`67115ab`](https://github.com/SimonLou-Dev/labomatics/commit/67115ab51b2c451c753c8552350c300e9b724443))

- Vm stop/delete with proper task wait and node selection
  ([`4fb5b1f`](https://github.com/SimonLou-Dev/labomatics/commit/4fb5b1f60ba2f74f288ee92ed5ae186af25cc7cd))

- Fixed VM stop to wait for task completion before returning - Removed skiplock parameter (requires
  root), use simple stop API - Added logging for VM stop/delete operations - Fixed pick_node() to
  disable cache and properly calculate node load - Removed manual LabVm deletion (cascade on
  LabProvisioning delete) - Added confirmation dialogs for redeploy lab and delete user - Improved
  node selection by memory availability

Backend changes: - vm.stop() now awaits task completion - vm.delete() calls stop before deletion -
  pick_node() uses live CLUSTER_RESOURCES data, selects by memory - Student cleanup simplified
  (removed unused LabVmRepository calls)

Frontend changes: - Added confirmation popups for redeploy/delete actions - Uses global
  ConfirmDialog from App.vue


## v0.4.0-rc.9 (2026-09-09)

### Bug Fixes

- Append migrations to docker image
  ([`1ef8560`](https://github.com/SimonLou-Dev/labomatics/commit/1ef85609c127777acf303a96a1c8976b6a2ec176))


## v0.4.0-rc.8 (2026-09-09)

### Bug Fixes

- Docker images
  ([`d982e3d`](https://github.com/SimonLou-Dev/labomatics/commit/d982e3d3bbcfa2b580e3b377494dd290d428c43c))


## v0.4.0-rc.7 (2026-09-09)

### Bug Fixes

- Disable release
  ([`a1599af`](https://github.com/SimonLou-Dev/labomatics/commit/a1599af8f2cb7c9779bd55a2024d885c23baec3c))


## v0.4.0-rc.6 (2026-09-09)

### Bug Fixes

- Disable release
  ([`a35f9d2`](https://github.com/SimonLou-Dev/labomatics/commit/a35f9d2d3ebb7b1d9db0cf717a7133982d10fc5b))


## v0.4.0-rc.5 (2026-09-09)

### Bug Fixes

- Disable release
  ([`771ca67`](https://github.com/SimonLou-Dev/labomatics/commit/771ca67c8e0a6362e4f3479eb1fa9205e6df81d4))


## v0.4.0-rc.4 (2026-09-09)

### Bug Fixes

- Use poetry
  ([`eb9f5ea`](https://github.com/SimonLou-Dev/labomatics/commit/eb9f5eac1da4b9ed06b1803868ca7f5079963371))


## v0.4.0-rc.3 (2026-09-09)

### Bug Fixes

- Use poetry
  ([`3967c9c`](https://github.com/SimonLou-Dev/labomatics/commit/3967c9c2cfdd37661f760cba54a07b89757e591f))


## v0.4.0-rc.2 (2026-09-09)

### Bug Fixes

- Compose
  ([`eed1467`](https://github.com/SimonLou-Dev/labomatics/commit/eed1467da089e5167afd9d1ebe888ace35e286d6))


## v0.4.0-rc.1 (2026-09-09)

### Bug Fixes

- Ajouter ID comme identifiant stable pour matching lors du diff import
  ([`3e1b60b`](https://github.com/SimonLou-Dev/labomatics/commit/3e1b60b915b80057e8faa930faefa69bb1ee2e6f))

- Ajouter 'id' (colonne mappable) aux requiredFields - L'ID devient le login stable de l'étudiant -
  Utiliser ID comme clé de matching (au lieu de email) pour comparaisons diffs - Service: indexer
  par login (qui vient de l'ID du CSV) pour matching stable - Routes: accepter paramètre 'id'
  obligatoire

- Align frontend types with backend LabDataDTO structure
  ([`0e2c313`](https://github.com/SimonLou-Dev/labomatics/commit/0e2c3137f9683a5f343f43abf2e6b1e61ffd1bf0))

- Remove wan_ip and vxlan_tag from StudentDetailDTO - Add wan_ip, vxlan_tag, openwrt_link to
  LabDataDTO - Fix LabVmDTO field names (memory/disk instead of memory_mb/disk_gb)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Améliorer logique d'attachement du disque après import
  ([`741c4c0`](https://github.com/SimonLou-Dev/labomatics/commit/741c4c0c5a62e9fe54ce95810fffaa9fcdb1d569))

Récupère le premier disque 'unused' après l'import et l'attache à scsi0, plutôt que de faire une
  hypothèse sur le nom du disque.

- Change dnstemplate
  ([`d4f1cd9`](https://github.com/SimonLou-Dev/labomatics/commit/d4f1cd98cfb0e59421017af2b748122c4649116a))

- Change order
  ([`b554e14`](https://github.com/SimonLou-Dev/labomatics/commit/b554e141e96d02e97f4c819180ceec29eed3d252))

- Check token existence by listing instead of direct access to avoid 500 error
  ([`0c4e438`](https://github.com/SimonLou-Dev/labomatics/commit/0c4e438f8b7aebf7a1211f4be59ea3e68353fd80))

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Ci not release dev
  ([`893cd12`](https://github.com/SimonLou-Dev/labomatics/commit/893cd12e27cf1754f876ce337805a7ed82dc3d07))

- Ci repo lower
  ([`b7f6112`](https://github.com/SimonLou-Dev/labomatics/commit/b7f6112cb2b64398f62374c6896356d56cb45877))

- Correction des routes GET /ip-ranges et /vxlan-ranges, refresh token en dev
  ([`97db8f3`](https://github.com/SimonLou-Dev/labomatics/commit/97db8f3a3f6642495f73cfa1581952c7c3a8ba05))

- GET /ip-ranges/{id} et GET /vxlan-ranges/{id}: corrigé auth (CurrentUser au lieu de
  RequireManageCluster), enlevé paramètre dto inutile - Services: charger les allocations utilisées
  quand on récupère une range par ID pour calculation correcte de utilization_percent -
  IpAllocationDTO: renommé champ 'ip' en 'ip_address' pour cohérence frontend - AuthMiddleware:
  amélioré la logique de refresh token (catch HTTPException directement, meilleur logging) - auth.py
  callback + middleware: cookies HTTPOnly avec secure=False en développement, secure=True en
  production - settings.py: ajouté alias ENVIRONMENT pour pouvoir configurer via .env

- Display lab data correctly using PrimeVue Card slots
  ([`4fa79b4`](https://github.com/SimonLou-Dev/labomatics/commit/4fa79b4051f3238552bd8696aaa9b8a62e735e9a))

- Use Card #title and #content slots properly - Fix data binding paths (wan_ip and vxlan_tag at root
  level, not in student) - Fix DataTable field names (memory/disk instead of memory_mb/disk_gb)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Docker ci
  ([`7a9b895`](https://github.com/SimonLou-Dev/labomatics/commit/7a9b895a3d45c6ef7d26ed087202bc7870261893))

- Linting
  ([`8fb8b3e`](https://github.com/SimonLou-Dev/labomatics/commit/8fb8b3ebaea44e0aadd28fe5ef22101819b468ca))

- Lors de l'init du cluster, exclusion de la première IP WAN
  ([`098a9ac`](https://github.com/SimonLou-Dev/labomatics/commit/098a9ac36c7f4d1794c5ba3aa120823fef40cd39))

- Template de l'env du backend
  ([`d813243`](https://github.com/SimonLou-Dev/labomatics/commit/d8132431b397e5c015253833d65339531028fc50))

- Update doc
  ([`8a64ea5`](https://github.com/SimonLou-Dev/labomatics/commit/8a64ea53ef936ea5ec884218f985889d1cb6d3c0))

- Update wf
  ([`2057c5c`](https://github.com/SimonLou-Dev/labomatics/commit/2057c5c72c7ac9637ac9eb101277e9e0883324b7))

- Use keycloak realm instead of hardcoded 'pve' for Proxmox user creation
  ([`93adfc3`](https://github.com/SimonLou-Dev/labomatics/commit/93adfc339567259f9d62463fbc0f2f9eb1c9ce1d))

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Utiliser wget + qm importdisk pour importer images cloud-init
  ([`f5b44ab`](https://github.com/SimonLou-Dev/labomatics/commit/f5b44abd76667705ff50fa65415e10d923e9cfed))

Remplace la méthode /download-url de Proxmox (qui échoue pour Fedora) par : 1. wget dans /tmp/ du
  nœud Proxmox 2. qm importdisk pour importer le disque qcow2 3. Attacher le disque à la VM créée

Nouvelle signature de VMDeployer.deploy() accepte image_path (chemin local du qcow2)

- **backend**: Csrf middleware, pagination, and security
  ([`5bc3834`](https://github.com/SimonLou-Dev/labomatics/commit/5bc3834d7607571aa2c3f640a6669bdf33efed2b))

- Fix CSRF middleware logic to properly handle token validation - Generate and expose CSRF token on
  all responses for SPA frontend - Add proxmoxer dependency for cluster connection testing - Add
  cluster_config_path setting for bootstrap configuration - Add encryption module for Proxmox API
  token secrets using Fernet - Enhance repository paginate() to support eager-loading relations

- **backend**: Timestamp timezone consistency and model corrections
  ([`28c466b`](https://github.com/SimonLou-Dev/labomatics/commit/28c466b04330ff392e9fa580e7ad268648f0ae2f))

- Change TimestampMixin to use naive UTC datetimes (datetime.utcnow().replace(tzinfo=None)) - Fixes
  mismatch with PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns - Remove unnecessary imports and
  clean up model definitions - Ensure all timestamp fields are consistently timezone-naive

- **build-template**: Nœud de build = nœud de connexion API (plus de pick_node aléatoire)
  ([`cc545ce`](https://github.com/SimonLou-Dev/labomatics/commit/cc545ce1cb61a3d1cd3c8e1a632a3c3d52833f60))

Sur un cluster multi-nœuds, pick_node() pouvait choisir pve4 pour le build alors que labomatics
  tourne sur pve1 : téléchargement sur le mauvais nœud, virt-customize SSH sur le mauvais nœud.
  local_node() résout le nœud par correspondance hostname avec PROXMOX_HOST. fallback pick_node si
  aucune correspondance.

Le champ node: dans infra.yaml permet de forcer un nœud explicite.

Docs : ajout des prérequis stockage local (type import) + libguestfs-tools dans build-template.md et
  setup.md.

- **openwrt**: Basculer LuCI sur ports 1336 (HTTP) / 1337 (HTTPS)
  ([`a20d758`](https://github.com/SimonLou-Dev/labomatics/commit/a20d758614ecd25516832b92e4e3493fa4affcef))

- Config uhttpd: écoute sur 1336 et 1337 - Redirection HTTP → HTTPS maintenue - Firewall: autoriser
  les nouveaux ports depuis WAN - Docs: mise à jour des instructions d'accès LuCI

Closes #12 Closes #13

### Chores

- Append docker test
  ([`3e1a591`](https://github.com/SimonLou-Dev/labomatics/commit/3e1a591708d91ace3f44d5958369f36153448c0f))

- Append logos
  ([`540b1ca`](https://github.com/SimonLou-Dev/labomatics/commit/540b1ca2ca73a211de5f46c78235a3a5ff20aebb))

- Cleanup and consolidate dependencies
  ([`4c6070a`](https://github.com/SimonLou-Dev/labomatics/commit/4c6070a08d33296899231e6b5d466b243f0807af))

- Update poetry.lock with new dependencies (proxmoxer, pyyaml) - Update model __init__ exports for
  new models - Update students route with consistency improvements - Add lab.py DTO for lab details
  (placeholder) - Add lab_vm.py model (placeholder) - Remove deprecated Students.vue page (moved to
  admin/Students.vue) - Remove deprecated services/api.ts (migrated to api/ clients)

- Connecteur proxmox async
  ([`f7c4b85`](https://github.com/SimonLou-Dev/labomatics/commit/f7c4b853e7fe1000819a8549d0c78f4df53247c5))

- Full setupwith CLI
  ([`99daf91`](https://github.com/SimonLou-Dev/labomatics/commit/99daf910a396ed144cede124e4819572738d9ddc))

- Liting + typing backend
  ([`1b9387a`](https://github.com/SimonLou-Dev/labomatics/commit/1b9387a6faa3894fb4eda40e560a5aa00bf0e807))

- Liting + typing cli
  ([`e54d9a9`](https://github.com/SimonLou-Dev/labomatics/commit/e54d9a969664114c32abd096c47b170abbfea89e))

- Liting + typing front
  ([`0450fb4`](https://github.com/SimonLou-Dev/labomatics/commit/0450fb45bf0a8e48c02cc163477bc26291dbcf20))

- Service allocation (tag vxlan, subnet, ip wan)
  ([`95e3ce9`](https://github.com/SimonLou-Dev/labomatics/commit/95e3ce9c17122a91b397ecc94e7a732559d6e1cd))

- Service allocation (tag vxlan, subnet, ip wan)
  ([`b703291`](https://github.com/SimonLou-Dev/labomatics/commit/b703291b03240ab8786a4e1e54d7447c4ffbe9f0))

- Update lock
  ([`90c9bdd`](https://github.com/SimonLou-Dev/labomatics/commit/90c9bdde82992e40717b7cafd83be9704b5489d1))

- **backend**: Update config examples and gitignore
  ([`d5d460b`](https://github.com/SimonLou-Dev/labomatics/commit/d5d460b059011b2953a316dc82eb0956da70c433))

- Add CLUSTER_CONFIG_PATH to .env.example for bootstrap configuration - Update .gitignore patterns
  for new build artifacts

- **branding**: Design system showcase HTML avec couleurs et typographie
  ([`058f852`](https://github.com/SimonLou-Dev/labomatics/commit/058f8526ac084901e73181b4ffc9a6fcdf5f96cf))

- **branding**: Guide d'identité visuelle complet
  ([`c580d2b`](https://github.com/SimonLou-Dev/labomatics/commit/c580d2b95b4329fd8e7e7126343892f37995ba10))

### Continuous Integration

- Add perms
  ([`92f58dc`](https://github.com/SimonLou-Dev/labomatics/commit/92f58dc52a5018ad3981772f7a48e95b49890d67))

- Fix perms
  ([`9aafeda`](https://github.com/SimonLou-Dev/labomatics/commit/9aafeda357746f87a5a0cfe639216e841d6e698a))

- Fix perms
  ([`2723400`](https://github.com/SimonLou-Dev/labomatics/commit/2723400aada27e4aad8d7fbd02eb0fd1cb7aba26))

- Fix perms
  ([`99cfc23`](https://github.com/SimonLou-Dev/labomatics/commit/99cfc231d121e5eb48c6fa8896891bdcd9041c04))

- Fix perms
  ([`77b73bb`](https://github.com/SimonLou-Dev/labomatics/commit/77b73bb851df8e16042734dbcc0f2ceacb6fc29f))

- Fix perms
  ([`2dc34ba`](https://github.com/SimonLou-Dev/labomatics/commit/2dc34ba0555596ab99441303fc2f82f19936ecec))

- Fix perms
  ([`00d6803`](https://github.com/SimonLou-Dev/labomatics/commit/00d6803433cfa56d0502401c15313d5f21f08521))

- Linting
  ([`a8afa65`](https://github.com/SimonLou-Dev/labomatics/commit/a8afa654d0f1fb639b2f94f0ed8dbf7aebf5cca4))

- Linting
  ([`50f7b5e`](https://github.com/SimonLou-Dev/labomatics/commit/50f7b5ea269adc6038854c9ffff7c7aac9c0fca7))

- Linting
  ([`ffed6ed`](https://github.com/SimonLou-Dev/labomatics/commit/ffed6eda7bf33a0e486f25caf905c74bf0d9bfcc))

- Update ci path
  ([`03da6d9`](https://github.com/SimonLou-Dev/labomatics/commit/03da6d9e45247b78921c6baf271bdd6a52207375))

- Update wf
  ([`56b5974`](https://github.com/SimonLou-Dev/labomatics/commit/56b59749659f71744e39ccbecbbf01c8a84bcbc4))

### Documentation

- **evolution**: Document v0.4 implementation progress
  ([`1fd435e`](https://github.com/SimonLou-Dev/labomatics/commit/1fd435e77d47423ca6577639bc3181ca496ab7aa))

- labomatics install CLI infrastructure complete - Modular architecture and idempotent operations -
  Full Keycloak and Proxmox OIDC integration - Multi-cluster support via terraform

### Features

- Add frontend components and flows for lab management
  ([`edfa961`](https://github.com/SimonLou-Dev/labomatics/commit/edfa961b862936392276782d44e77d3805c0362a))

- Add API clients for labs and cohorts (frontend) - Add Lab page and related components - Add menu
  item for lab access - Add Cohorts admin page - Update OpenWrt init script documentation

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Add lab creation API endpoints and database migrations
  ([`aba5e8f`](https://github.com/SimonLou-Dev/labomatics/commit/aba5e8f8773b02376745fc04784cbf2c7b332908))

- Create POST /labs endpoint for lab creation - Create GET /labs/me endpoint to fetch user's lab
  data - Add database migration for owner-generic pattern - Add cachetools dependency for asyncpg -
  Improve worker job orchestration

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Add LabService, AuditService and new enums for lab creation workflow
  ([`e4d9d05`](https://github.com/SimonLou-Dev/labomatics/commit/e4d9d054de635c2e71c38c73f15d3dffaea915cd))

- Add OwnerRole enum (STUDENT, TEACHER, ADMIN) - Add EventType enum for audit trail (LAB_REQUESTED,
  WAN_IP_ALLOCATED, etc) - Create AuditService for event logging - Create LabService for
  orchestrating lab creation - Improve VxlanRangeService with proper repository initialization

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Add LDAP, RADIUS, and Docker installation to CLI installer
  ([`f4fb7cf`](https://github.com/SimonLou-Dev/labomatics/commit/f4fb7cfa07b794d11464610f8d062b4972ce0535))

Add OpenLDAP and FreeRADIUS services to the Docker Compose stack with: - OpenLDAP
  (bitnami/openldap:2.6) with LDAPS support via CA-signed certificates - FreeRADIUS
  (freeradius/freeradius-server:3.2.5) with PAP authentication via LDAP bind - Keycloak LDAP User
  Federation (WRITABLE mode) for bidirectional sync - LDAP Group Mapper for group synchronization
  between LDAP and Keycloak - TLS encryption for LDAP/RADIUS using the existing PKI infrastructure

Fix the broken Docker installation pipeline: - Install Docker Engine and docker-compose-plugin via
  dnf in NetworkSetup - Upload docker-compose.yml, init-databases.sh, dynamic.yml, and config files
  before docker compose up - Extend certificate generation to include ldap.{domain} and DNS:ldap SAN
  entries

Add step 9 for LDAP/RADIUS configuration: - Collect Base DN (auto-derived from domain), service
  account passwords, and RADIUS shared secret - Generate cryptographically-secure secrets via
  secrets.token_urlsafe() - Update all step counters from 8 to 9 for progress display

Extend KeycloakClient with LDAP federation methods: - create_ldap_federation(): Configure User
  Federation WRITABLE provider - create_group_ldap_mapper(): Configure bidirectional group sync
  (LDAP_ONLY mode)

Add ServiceVerifier.wait_for_tcp_port() for LDAP readiness check before Keycloak config.

Files modified: - templates/docker-compose.yml: Add ldap and radius services -
  templates/ldap-bootstrap.ldif: LDIF seed for LDAP directory structure -
  templates/radius-clients.conf: RADIUS client config - templates/radius-mods-ldap: FreeRADIUS LDAP
  module config for PAP auth - templates/radius-site-default: FreeRADIUS site config -
  commands/install/network.py: Docker installation and compose file upload -
  commands/install/steps.py: Step 9 (LDAP/RADIUS config collection) -
  commands/install/certificates.py: LDAP certificate generation - commands/install/ldap_setup.py:
  LDAP readiness verification - commands/install/keycloak.py: LDAP federation setup -
  commands/install/orchestrator.py: Step 9 integration, LDAP wait, federation config -
  utils/keycloak.py: LDAP federation API methods - utils/verify.py: TCP port availability check -
  utils/ldap_utils.py: domain_to_base_dn() utility

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

Claude-Session: https://claude.ai/code/session_01SfG8ZALzU4MMz7TH6TaNur

- Add owner-generic pattern to database models for multi-role lab support
  ([`7bbbbdb`](https://github.com/SimonLou-Dev/labomatics/commit/7bbbbdb15f71fdcbe25feaaa76a466aee6b94109))

- Add owner_keycloak_id and owner_role to LabProvisioning, IpAllocation, VxlanAllocation - Make
  student_id nullable to support teacher/admin owners - Add is_default boolean to CohortCluster for
  cluster-per-cohort defaulting - Add eager-loading repository methods to prevent
  DetachedInstanceError

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Ajout client API brevo + SMPT config pour keycloak
  ([`1f50950`](https://github.com/SimonLou-Dev/labomatics/commit/1f5095038840b0c809069b820384355c4c146fc1))

- Ajout du backend + UI
  ([`57a8e61`](https://github.com/SimonLou-Dev/labomatics/commit/57a8e615e22151a2b36f0bb28a0f7b83f01767ad))

BREAKING CHANGE: passe à la v1 avec l'ajout de l'ui

- Construction de la vm openwrt template lors de l'install
  ([`f193bac`](https://github.com/SimonLou-Dev/labomatics/commit/f193bac752c72f899b5472cbcfa65a3a619990bd))

- Implémenter l'infrastructure labomatics install
  ([`c8ab638`](https://github.com/SimonLou-Dev/labomatics/commit/c8ab63882213edafdb4fce7d1bd485fc2fe81e33))

- Provisionnement de la VM via cloud-init - Configuration Keycloak (realms, groupes, rôles, client
  OIDC) - Configuration authentification OIDC Proxmox - Certificats TLS auto-signés avec DNS dnsmasq
  - Configuration zone SDN VXLAN et nœuds - Accès SSH par nœud avec demande MDP - Génération
  idempotente des certificats - Suivi d'état pour installations résumables

Closes #15 #22 #23

- Interface multi-étapes d'import XML pour étudiants
  ([`d15275b`](https://github.com/SimonLou-Dev/labomatics/commit/d15275b256fa484ef7e05005ee2488bc0cc49c04))

Frontend: - StudentImportDialog.vue: composant avec 4 étapes (upload, mapping, vérification,
  confirmation) - Tableaux de diff avec filtre par statut et recherche par nom - Affichage des
  ajoutés/modifiés/supprimés avec détails - Page Students.vue: ajout du bouton 'Importer XML' -
  Types + API pour l'import XML (previewStudentImport, applyStudentImport)

Backend: - StudentImportService: parsing XML, calcul du diff (added/modified/deleted) - Routes POST
  /students/import-xml/preview et /apply avec Form mapping - DTO StudentImportDiffDTO pour résultat
  (added/modified/deleted/errors)

Note: l'applique de l'import (sauvegarde en DB) est TODO

- Linting
  ([`16f5fdc`](https://github.com/SimonLou-Dev/labomatics/commit/16f5fdc9fc69291f52647ed6f2b16f0e343770eb))

- **backend**: Admin infrastructure for clusters, IP ranges, and VXLAN ranges
  ([`ba1fa7c`](https://github.com/SimonLou-Dev/labomatics/commit/ba1fa7c1258c38dd905706b17764025c2d830c0b))

- Add DTOs for cluster management with credentials and range attachments - Add DTOs for IP ranges
  and VXLAN ranges with allocations - Add pagination DTO for paginated responses - Add services for
  CRUD operations on clusters, ranges, and config bootstrap - Add cluster credential
  encryption/decryption support - Add cluster config parsing and idempotent bootstrap from YAML -
  Services support range attachment, credential management, and connection testing

- **backend**: Ajouter liste étudiants paginée avec IP WAN et VNI
  ([`0bb8a5b`](https://github.com/SimonLou-Dev/labomatics/commit/0bb8a5b6882d1ebdf74c752c0add23a32064f6e1))

- StudentService + DTO pour la liste paginée avec pagination - Route GET /v1/students?page=size
  retourne étudiants avec cohort + IP WAN + VNI - StudentRepository.list_with_pagination() avec
  jointures SQL optimisées - Réparer relationships cassées: IpAllocation et VxlanAllocation -
  Enlever back_populates cassés dans IpRange et VxlanRange

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **backend**: Api routes for cluster and range management
  ([`577647e`](https://github.com/SimonLou-Dev/labomatics/commit/577647e351253b129ff91741a4cfa685f0ea1f01))

- Add GET/POST/PATCH/DELETE routes for clusters with pagination - Add routes for credential
  management and Proxmox connection testing - Add routes for attaching/detaching IP ranges and VXLAN
  ranges - Add routes for cluster config upload and application - Add GET/POST/PATCH/DELETE routes
  for IP ranges and VXLAN ranges - All list endpoints return paginated responses - Secure mutations
  with manage_cluster role requirement

- **backend**: Bootstrap cluster config and RBAC for admin
  ([`7f52f9c`](https://github.com/SimonLou-Dev/labomatics/commit/7f52f9c2ed3794a110edfa1301de44f5967cc894))

- Add cluster config bootstrap at startup (idempotent, one-shot) - Add manage_cluster role for
  administrative operations - Register new services (Cluster, IpRange, VxlanRange, ClusterConfig) as
  dependencies - Services auto-wire to repositories and other dependencies

- **backend**: Implémenter auth, RBAC, student import, mail service
  ([`a0dc906`](https://github.com/SimonLou-Dev/labomatics/commit/a0dc906feae965242e435c472ba696ba4f3536af))

- JWT authentication + role-based access control (RBAC) - AuthService: decode token, ensure role,
  exchange code for token - StudentImportService: preview/apply CSV import avec validation -
  MailService: stub avec TODO pour SMTP réel - KeycloakAdminConnector: create/delete user, manage
  groups/roles - DTO: AuthUser, MeDTO, StudentImportMapping, StudentImportDiff - Middlewares: JWT
  verification et role extraction - Routes: /me, /students/import/preview, /students/import/apply -
  Settings: KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD - Alembic migrations initiales

Fixes #17, #24, #19, #20, #21

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **backend**: Vxlan MTU migration and cluster bootstrap configuration
  ([`2214015`](https://github.com/SimonLou-Dev/labomatics/commit/22140152cef00625ae993d3d298e09f8e7431316))

- Add Alembic migration to add mtu field to vxlan_range table (default 1350) - Add
  clusterconfig.example.yaml template for cluster bootstrap - Include example configuration for
  clusters, IP ranges, and VXLAN ranges - Template ready for deployment with CLUSTER_CONFIG_PATH
  environment variable

- **backend/frontend**: Student import complet + filtrage + cohort/cluster assign
  ([`5bcadf8`](https://github.com/SimonLou-Dev/labomatics/commit/5bcadf8b9d7d578f7e53e53e705aba5c98278602))

- StudentService: create/update/delete avec Keycloak + password + mail - Login auto:
  firstname.lastname (non-modifiable) - Cohort/Enrollment idempotent + année scolaire 01/09-31/08 -
  User ajouté groupe 'student' automatiquement - Cohort assigné au cluster par défaut - Frontend:
  tri par nom, filtrage par promo, recherche globale (nom/email/IP) - Recherche backend sur tous les
  étudiants, pas juste la page actuelle - Enrollment actif détecté par dates, pas end_date is None -
  Eager load relations pour éviter DetachedInstanceError

- **cli**: Ajouter compte technique keycloak + permissions realm-management
  ([`3e9d5ee`](https://github.com/SimonLou-Dev/labomatics/commit/3e9d5ee793389650036da7fc7d2b874461d16510))

- Creation user labomatics-admin (password non-temporaire) - Assignment des 4 rôles
  realm-management: manage-users, view-users, manage-clients, view-clients - Methodes
  KeycloakClient: get_client_uuid, assign_client_role_to_user - Affichage credentials en fin
  d'install (username + password en couleur) - Role manage_user assigné au groupe superadmin

Fixes #17, #24

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **cli**: Scaffold v0.4 avec commande install + cloud-init Alpine
  ([`d8bbe52`](https://github.com/SimonLou-Dev/labomatics/commit/d8bbe523176cbbac1cea2815940d56a5676ff8d5))

- **cli**: Update schema and keycloak setup for admin roles
  ([`126f7f9`](https://github.com/SimonLou-Dev/labomatics/commit/126f7f990254bc00faea1fa603bac0278382b10b))

- Update VnetConfig with vni_min, vni_max fields - Update ClusterEntry with sdn_zone, token_id,
  token_secret fields - Update ConfigGenerator to pass these fields to templates - Add
  manage_cluster role creation in keycloak setup - Assign manage_cluster role to superadmin group -
  Add user existence check before creating new users

- **db**: Modèle de données SQLAlchemy v0.4-v0.5
  ([`48030d1`](https://github.com/SimonLou-Dev/labomatics/commit/48030d13f5b8c21eaecc2fdcd383a3b086e1dce4))

- 16 modèles SQLAlchemy: 6 identité, 2 sécurité, 8 provisioning - 16 repositories avec pattern
  générique BaseRepository - Migrations Alembic: identité, sécurité, provisioning multi-cluster -
  Index uniques partiels pour historique (enrollment, allocations) - Chiffrement Fernet pour secrets
  cluster

Resolves #16

- **frontend**: Add Lab page placeholder
  ([`02626ff`](https://github.com/SimonLou-Dev/labomatics/commit/02626ff222a9f290b33d9497fa7d717a963602e4))

- Add Lab.vue page for individual student lab details - Accessible at /lab/:userId route -
  Placeholder for future integration with lab provisioning data

- **frontend**: Admin pages for cluster and range management
  ([`b8b8986`](https://github.com/SimonLou-Dev/labomatics/commit/b8b898694c74e9eb05cb373bbdd1a692e07919aa))

- Add Clusters.vue with DataTable CRUD, credential management, range attachment - Add WanRanges.vue
  with IP range management and utilization progress bars - Add NetworkRanges.vue with VXLAN range
  management and utilization progress bars - Add WanRangeDetails.vue showing IP allocations with
  student info and links - Add NetworkRangeDetails.vue showing VNI allocations with student info -
  Add test connection button with Proxmox credentials verification - Add navigation to detail pages
  from management dialogs - Progress bars use orange color with border for visibility

- **frontend**: Api clients and types for cluster management
  ([`e055e8c`](https://github.com/SimonLou-Dev/labomatics/commit/e055e8c4e413fa89ec0caf3a65ae0cb25fb8d4c9))

- Add clusters.ts with CRUD operations, credential, range attachment, config upload - Add
  ipRanges.ts with CRUD and allocation retrieval - Add vxlanRanges.ts with CRUD and allocation
  retrieval - Add type definitions for all DTOs (ClusterDTO, IpRangeDTO, VxlanRangeDTO) - Add type
  definitions for credentials and allocations - All list operations support pagination

- **frontend**: Créer interface utilisateur complète avec primevue
  ([`d164e5b`](https://github.com/SimonLou-Dev/labomatics/commit/d164e5b85cd74d483fb647700ce66b3d83e6389b))

- Layout responsive: SidebarLayout, MainLayout avec navigation par rôle - Pages: Login (minimal),
  Dashboard (palette couleurs), Students (empty) - Theme system: light/dark/dyslexia modes avec
  localStorage persistence - Design system: couleur primaire orange (#FF6B00), surface steel - CSS
  variables RGB-space et Tailwind primary-lab/error-lab palette - PrimeVue Aura preset configuré
  avec custom theming - PrimeUI Community License management (.env.local) - Composables: useTheme
  (dark/dyslexia), useSidebar - Assets: logo.svg, logo-large.svg

Fixes #18

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **frontend**: Routes and global components for admin UI
  ([`f11e8cf`](https://github.com/SimonLou-Dev/labomatics/commit/f11e8cfdf48ac680f2b334c10b72fe0eaa8282c6))

- Add routes for /admin/cluster, /admin/wan, /admin/networks, /lab/:userId - Add routes for
  WanRangeDetails and NetworkRangeDetails with :rangeId param - Mount Toast and ConfirmDialog
  components globally for notifications - Add breadcrumb navigation in MainLayout - Export new API
  clients and types from index files

- **frontend**: Tableau Students avec pagination backend et coloration cohort
  ([`d0c9d0f`](https://github.com/SimonLou-Dev/labomatics/commit/d0c9d0f744a892a7a0a33c167b7704b3ec5c31e5))

- Service API pour récupérer liste paginée des étudiants du backend - Refactor Students.vue:
  DataTable paginée + colonnes IP WAN + VNI - Utility getCohortColor() pour colorer badges cohort de
  manière stable (hash) - Ajout credentials: 'include' pour envoyer cookies auth avec requête -
  Colonnes: ID | Login | Nom | Email | Promo (badge) | IP WAN | VNI | Actions

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **install**: Cli v0.4 complet + cloud-init + setup Keycloak + OIDC
  ([`ce82539`](https://github.com/SimonLou-Dev/labomatics/commit/ce825391e630676dfb332d64d013923e7345dbe1))

- **install**: Implémentation complète - Proxmox API + SSH upload + verification + error handling
  ([`83a7650`](https://github.com/SimonLou-Dev/labomatics/commit/83a7650404811fc33bce7c90d194a978a090011d))

### Refactoring

- Cleanup and improve Proxmox helper clients
  ([`aa66b80`](https://github.com/SimonLou-Dev/labomatics/commit/aa66b802aeb6c198868135d6a29f054a58171722))

- Remove unused import (re) from _root.py - Use contextlib.suppress for error handling in ACL client
  - Fix error messages to use actual userid variable - Add proper docstrings and error handling

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Exports et types API range (aucun changement de logique)
  ([`39a2c7e`](https://github.com/SimonLou-Dev/labomatics/commit/39a2c7e7a04afbef659b5c522426d36d07bcc8fa))

- Simplifie detail pages et ranges list, utilise GET /id au lieu de lister
  ([`5737f0a`](https://github.com/SimonLou-Dev/labomatics/commit/5737f0abd6e3b212ff551964d0a9bf1890b0505a))

Frontend: - WanRangeDetails, NetworkRangeDetails: utilise getIpRange(id) / getVxlanRange(id) au lieu
  de lister tout et chercher - Clusters.vue: corrigé nom champ 'storage' -> 'default_storage' dans
  formData - WanRanges, NetworkRanges: remplacé ProgressBar slot template (inexistant) par div avec
  linear gradient pour affichage du %

- **backend**: Use generic pagination and fix repository patterns
  ([`6a49511`](https://github.com/SimonLou-Dev/labomatics/commit/6a49511cbf3cfc6a10a9a3ee9d0121d077422d55))

- Use BaseRepository.paginate() with relations for StudentService - Remove
  StudentRepository.list_with_pagination (replaced by generic paginate) - Add order_by support to
  BaseRepository.paginate() - Add IntegrityError handling to BaseRepository.delete() returning 409 -
  Normalize IP allocation filters for consistency - Student pagination now uses generic selectinload
  for relations

- **frontend**: Standardize student API to use http client
  ([`c4cbf93`](https://github.com/SimonLou-Dev/labomatics/commit/c4cbf93813b8cc7744bf73d803274e3e4faff7c6))

- Add listStudents() returning PaginatedResponse<StudentListItem> - Add StudentListItem interface
  for list responses - Use http.ts client instead of direct fetch - Maintain pagination fields
  (page, per_page, total, total_pages) - Follow consistent API naming conventions across all domains

- **monorepo**: Déplacer labomatics/ → old_cli/labomatics/ pour v0.4
  ([`73349e5`](https://github.com/SimonLou-Dev/labomatics/commit/73349e5e657ddfcb212973c50661381126a88303))

- **monorepo**: Pyproject.toml → old_cli/, supprimer systemd/
  ([`c74fbbf`](https://github.com/SimonLou-Dev/labomatics/commit/c74fbbf3e905d17f047e7bad2e7e2e6ca528995b))


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

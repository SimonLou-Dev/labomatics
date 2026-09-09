# CHANGELOG


## v0.4.0-rc.6 (2026-09-09)

### Bug Fixes

- Lors de l'init du cluster, exclusion de la première IP WAN
  ([`7b65b24`](https://github.com/SimonLou-Dev/labomatics/commit/7b65b2446b2d6958b4ed547565a06075b8a16d50))

- Template de l'env du backend
  ([`23c462d`](https://github.com/SimonLou-Dev/labomatics/commit/23c462d19f02e604f4ab9ad4e0fa2e1efa4f8096))


## v0.4.0-rc.5 (2026-09-08)

### Bug Fixes

- Ci repo lower
  ([`861de0b`](https://github.com/SimonLou-Dev/labomatics/commit/861de0bd97c3cbe49c7ee2d1a943f790237a41a0))

- Update wf
  ([`b5780ab`](https://github.com/SimonLou-Dev/labomatics/commit/b5780abba102be0d394722f89a4f56c0ce7ce5a7))

### Continuous Integration

- Add perms
  ([`56b5cb4`](https://github.com/SimonLou-Dev/labomatics/commit/56b5cb4526c2fd000d6652bc77a9ca39a548714c))

- Update wf
  ([`c8a169c`](https://github.com/SimonLou-Dev/labomatics/commit/c8a169cdf9b5c886698da4b256a354b56d9437a2))


## v0.4.0-rc.4 (2026-09-08)

### Continuous Integration

- Update ci path
  ([`d63904b`](https://github.com/SimonLou-Dev/labomatics/commit/d63904b8cf0245e883cebe3008462681cc0d6531))

### Features

- Ajout du backend + UI
  ([`3aee7a6`](https://github.com/SimonLou-Dev/labomatics/commit/3aee7a697c7a690f6f860f302ac1fc8a959961bb))

BREAKING CHANGE: passe à la v1 avec l'ajout de l'ui

### Breaking Changes

- Passe à la v1 avec l'ajout de l'ui


## v0.4.0-rc.3 (2026-09-08)

### Bug Fixes

- Update doc
  ([`e5f27e2`](https://github.com/SimonLou-Dev/labomatics/commit/e5f27e202cac3a7981a62ba87fecef96a9668920))


## v0.4.0-rc.2 (2026-09-08)

### Bug Fixes

- Ci not release dev
  ([`a991823`](https://github.com/SimonLou-Dev/labomatics/commit/a991823c555059ba7578c1c13713aa56946077f1))

### Chores

- Full setupwith CLI
  ([`deae8d7`](https://github.com/SimonLou-Dev/labomatics/commit/deae8d72c4f6465eb9f2ef3b3a32fad2d8971e2a))


## v0.4.0-rc.1 (2026-09-08)

### Bug Fixes

- Ajouter ID comme identifiant stable pour matching lors du diff import
  ([`d645629`](https://github.com/SimonLou-Dev/labomatics/commit/d645629e8ecd6b17d243a404eca9fb41d11058b9))

- Ajouter 'id' (colonne mappable) aux requiredFields - L'ID devient le login stable de l'étudiant -
  Utiliser ID comme clé de matching (au lieu de email) pour comparaisons diffs - Service: indexer
  par login (qui vient de l'ID du CSV) pour matching stable - Routes: accepter paramètre 'id'
  obligatoire

- Align frontend types with backend LabDataDTO structure
  ([`17315eb`](https://github.com/SimonLou-Dev/labomatics/commit/17315ebce60028f72616588b278849ce972267d1))

- Remove wan_ip and vxlan_tag from StudentDetailDTO - Add wan_ip, vxlan_tag, openwrt_link to
  LabDataDTO - Fix LabVmDTO field names (memory/disk instead of memory_mb/disk_gb)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Check token existence by listing instead of direct access to avoid 500 error
  ([`9215a6a`](https://github.com/SimonLou-Dev/labomatics/commit/9215a6a1c0784b8a94739407919a6dafbb188d21))

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Correction des routes GET /ip-ranges et /vxlan-ranges, refresh token en dev
  ([`769f9a2`](https://github.com/SimonLou-Dev/labomatics/commit/769f9a2612637c6bf2d9fe88ad4b1b9fefe9bf49))

- GET /ip-ranges/{id} et GET /vxlan-ranges/{id}: corrigé auth (CurrentUser au lieu de
  RequireManageCluster), enlevé paramètre dto inutile - Services: charger les allocations utilisées
  quand on récupère une range par ID pour calculation correcte de utilization_percent -
  IpAllocationDTO: renommé champ 'ip' en 'ip_address' pour cohérence frontend - AuthMiddleware:
  amélioré la logique de refresh token (catch HTTPException directement, meilleur logging) - auth.py
  callback + middleware: cookies HTTPOnly avec secure=False en développement, secure=True en
  production - settings.py: ajouté alias ENVIRONMENT pour pouvoir configurer via .env

- Display lab data correctly using PrimeVue Card slots
  ([`984b53a`](https://github.com/SimonLou-Dev/labomatics/commit/984b53a21fbda1fbc8c9bb062626b351d521d096))

- Use Card #title and #content slots properly - Fix data binding paths (wan_ip and vxlan_tag at root
  level, not in student) - Fix DataTable field names (memory/disk instead of memory_mb/disk_gb)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Use keycloak realm instead of hardcoded 'pve' for Proxmox user creation
  ([`2e85a0d`](https://github.com/SimonLou-Dev/labomatics/commit/2e85a0d3a515848195e7b406cf0de1199cabdca1))

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **backend**: Csrf middleware, pagination, and security
  ([`9e32e81`](https://github.com/SimonLou-Dev/labomatics/commit/9e32e817c206d095c2c38fa475f6edc3af91d743))

- Fix CSRF middleware logic to properly handle token validation - Generate and expose CSRF token on
  all responses for SPA frontend - Add proxmoxer dependency for cluster connection testing - Add
  cluster_config_path setting for bootstrap configuration - Add encryption module for Proxmox API
  token secrets using Fernet - Enhance repository paginate() to support eager-loading relations

- **backend**: Timestamp timezone consistency and model corrections
  ([`192e32a`](https://github.com/SimonLou-Dev/labomatics/commit/192e32a422d8ea8ecdf724fca55916a5d91329ee))

- Change TimestampMixin to use naive UTC datetimes (datetime.utcnow().replace(tzinfo=None)) - Fixes
  mismatch with PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns - Remove unnecessary imports and
  clean up model definitions - Ensure all timestamp fields are consistently timezone-naive

- **build-template**: Nœud de build = nœud de connexion API (plus de pick_node aléatoire)
  ([`a51d105`](https://github.com/SimonLou-Dev/labomatics/commit/a51d1052dfc7fbebae1ce65eef7305d206241f62))

Sur un cluster multi-nœuds, pick_node() pouvait choisir pve4 pour le build alors que labomatics
  tourne sur pve1 : téléchargement sur le mauvais nœud, virt-customize SSH sur le mauvais nœud.
  local_node() résout le nœud par correspondance hostname avec PROXMOX_HOST. fallback pick_node si
  aucune correspondance.

Le champ node: dans infra.yaml permet de forcer un nœud explicite.

Docs : ajout des prérequis stockage local (type import) + libguestfs-tools dans build-template.md et
  setup.md.

- **openwrt**: Basculer LuCI sur ports 1336 (HTTP) / 1337 (HTTPS)
  ([`a2c7081`](https://github.com/SimonLou-Dev/labomatics/commit/a2c708156353a95406b2f0e1ffc7a3c101e1eb1a))

- Config uhttpd: écoute sur 1336 et 1337 - Redirection HTTP → HTTPS maintenue - Firewall: autoriser
  les nouveaux ports depuis WAN - Docs: mise à jour des instructions d'accès LuCI

Closes #12 Closes #13

### Chores

- Append docker test
  ([`2c821ba`](https://github.com/SimonLou-Dev/labomatics/commit/2c821bad9fa79ab9d30055f47942d8c9e8a7b84f))

- Append logos
  ([`c55273e`](https://github.com/SimonLou-Dev/labomatics/commit/c55273e23bd0e036f01858eb9170290b348c2481))

- Cleanup and consolidate dependencies
  ([`41bd1cc`](https://github.com/SimonLou-Dev/labomatics/commit/41bd1cc30fb6b305415070d41b03761716880f93))

- Update poetry.lock with new dependencies (proxmoxer, pyyaml) - Update model __init__ exports for
  new models - Update students route with consistency improvements - Add lab.py DTO for lab details
  (placeholder) - Add lab_vm.py model (placeholder) - Remove deprecated Students.vue page (moved to
  admin/Students.vue) - Remove deprecated services/api.ts (migrated to api/ clients)

- Connecteur proxmox async
  ([`9cc6d19`](https://github.com/SimonLou-Dev/labomatics/commit/9cc6d19d778e648cb9f03dcfb3cec6ae4bf2601f))

- Liting + typing backend
  ([`4940b9f`](https://github.com/SimonLou-Dev/labomatics/commit/4940b9fb795ab9d9ce2a2626391710d7f09c45bd))

- Liting + typing cli
  ([`64b5882`](https://github.com/SimonLou-Dev/labomatics/commit/64b5882af4a72036b01354065f302480a537a653))

- Liting + typing front
  ([`81efc2a`](https://github.com/SimonLou-Dev/labomatics/commit/81efc2a225c473abe20172b5de8b7a1d83c0097f))

- Service allocation (tag vxlan, subnet, ip wan)
  ([`bd1460a`](https://github.com/SimonLou-Dev/labomatics/commit/bd1460a1de99d760059ca40c4250a3b6638d9ca3))

- Service allocation (tag vxlan, subnet, ip wan)
  ([`9a99519`](https://github.com/SimonLou-Dev/labomatics/commit/9a99519b49861bcb107de375337d917b90ed991f))

- Update lock
  ([`d5b141a`](https://github.com/SimonLou-Dev/labomatics/commit/d5b141a28e601b3adb0ebe9d835711fb85dad100))

- **backend**: Update config examples and gitignore
  ([`e7b979a`](https://github.com/SimonLou-Dev/labomatics/commit/e7b979acdb67b6e05886ca37c2c42a5eef193505))

- Add CLUSTER_CONFIG_PATH to .env.example for bootstrap configuration - Update .gitignore patterns
  for new build artifacts

- **branding**: Design system showcase HTML avec couleurs et typographie
  ([`4f0c773`](https://github.com/SimonLou-Dev/labomatics/commit/4f0c773eeb0625a621f5e0fb970699a6029a14ff))

- **branding**: Guide d'identité visuelle complet
  ([`aac078f`](https://github.com/SimonLou-Dev/labomatics/commit/aac078fee171e8284ee17da823129de38c0b070c))

### Continuous Integration

- Fix perms
  ([`141d159`](https://github.com/SimonLou-Dev/labomatics/commit/141d159ef5fd82c6b96c24960ce0fd665d79ccde))

- Fix perms
  ([`2e7a5ca`](https://github.com/SimonLou-Dev/labomatics/commit/2e7a5ca2e3194f9ae13a5a56e4a58d93fdce8564))

- Fix perms
  ([`a66308e`](https://github.com/SimonLou-Dev/labomatics/commit/a66308eb59456cb6befc031aecbc7cfcd26f62f8))

- Fix perms
  ([`676cf06`](https://github.com/SimonLou-Dev/labomatics/commit/676cf06777c8a62de88b0aa35303cb92a9df3591))

- Fix perms
  ([`634161f`](https://github.com/SimonLou-Dev/labomatics/commit/634161f23d464c2211dcf927ff5f818831827a1e))

- Fix perms
  ([`c4c906d`](https://github.com/SimonLou-Dev/labomatics/commit/c4c906d415e31bb13ccfccbf8498aaad6f066c32))

### Documentation

- **evolution**: Document v0.4 implementation progress
  ([`e72a0b0`](https://github.com/SimonLou-Dev/labomatics/commit/e72a0b0ce2f35bdbfb71a66695deb555bca1cf03))

- labomatics install CLI infrastructure complete - Modular architecture and idempotent operations -
  Full Keycloak and Proxmox OIDC integration - Multi-cluster support via terraform

### Features

- Add frontend components and flows for lab management
  ([`9fba775`](https://github.com/SimonLou-Dev/labomatics/commit/9fba7752cdd0d54a5cc8f783da40b46a7e0311ef))

- Add API clients for labs and cohorts (frontend) - Add Lab page and related components - Add menu
  item for lab access - Add Cohorts admin page - Update OpenWrt init script documentation

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Add lab creation API endpoints and database migrations
  ([`58113e2`](https://github.com/SimonLou-Dev/labomatics/commit/58113e2ee8f75afa32b53e68c7f862bd720b360e))

- Create POST /labs endpoint for lab creation - Create GET /labs/me endpoint to fetch user's lab
  data - Add database migration for owner-generic pattern - Add cachetools dependency for asyncpg -
  Improve worker job orchestration

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Add LabService, AuditService and new enums for lab creation workflow
  ([`99c4894`](https://github.com/SimonLou-Dev/labomatics/commit/99c4894fb308ec3625e8ea6fc719a40d02fc8f6c))

- Add OwnerRole enum (STUDENT, TEACHER, ADMIN) - Add EventType enum for audit trail (LAB_REQUESTED,
  WAN_IP_ALLOCATED, etc) - Create AuditService for event logging - Create LabService for
  orchestrating lab creation - Improve VxlanRangeService with proper repository initialization

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Add LDAP, RADIUS, and Docker installation to CLI installer
  ([`f564fac`](https://github.com/SimonLou-Dev/labomatics/commit/f564facecd83d4101fda8b1cbf544b31ca2b662a))

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
  ([`8ced4ad`](https://github.com/SimonLou-Dev/labomatics/commit/8ced4ad5be31797479a92154b94898a58b03439b))

- Add owner_keycloak_id and owner_role to LabProvisioning, IpAllocation, VxlanAllocation - Make
  student_id nullable to support teacher/admin owners - Add is_default boolean to CohortCluster for
  cluster-per-cohort defaulting - Add eager-loading repository methods to prevent
  DetachedInstanceError

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Construction de la vm openwrt template lors de l'install
  ([`f5eb20d`](https://github.com/SimonLou-Dev/labomatics/commit/f5eb20dad445a6d800d53f1a80c1fe22cee71d4e))

- Implémenter l'infrastructure labomatics install
  ([`0b4ae37`](https://github.com/SimonLou-Dev/labomatics/commit/0b4ae378df9457f4c3eea45246b4fb685e0835bd))

- Provisionnement de la VM via cloud-init - Configuration Keycloak (realms, groupes, rôles, client
  OIDC) - Configuration authentification OIDC Proxmox - Certificats TLS auto-signés avec DNS dnsmasq
  - Configuration zone SDN VXLAN et nœuds - Accès SSH par nœud avec demande MDP - Génération
  idempotente des certificats - Suivi d'état pour installations résumables

Closes #15 #22 #23

- Interface multi-étapes d'import XML pour étudiants
  ([`cf6cc61`](https://github.com/SimonLou-Dev/labomatics/commit/cf6cc611167d0876946422beab99096831aa7f8e))

Frontend: - StudentImportDialog.vue: composant avec 4 étapes (upload, mapping, vérification,
  confirmation) - Tableaux de diff avec filtre par statut et recherche par nom - Affichage des
  ajoutés/modifiés/supprimés avec détails - Page Students.vue: ajout du bouton 'Importer XML' -
  Types + API pour l'import XML (previewStudentImport, applyStudentImport)

Backend: - StudentImportService: parsing XML, calcul du diff (added/modified/deleted) - Routes POST
  /students/import-xml/preview et /apply avec Form mapping - DTO StudentImportDiffDTO pour résultat
  (added/modified/deleted/errors)

Note: l'applique de l'import (sauvegarde en DB) est TODO

- **backend**: Admin infrastructure for clusters, IP ranges, and VXLAN ranges
  ([`9094dae`](https://github.com/SimonLou-Dev/labomatics/commit/9094dae864d1d70f404e92fb008d4eb1d249e811))

- Add DTOs for cluster management with credentials and range attachments - Add DTOs for IP ranges
  and VXLAN ranges with allocations - Add pagination DTO for paginated responses - Add services for
  CRUD operations on clusters, ranges, and config bootstrap - Add cluster credential
  encryption/decryption support - Add cluster config parsing and idempotent bootstrap from YAML -
  Services support range attachment, credential management, and connection testing

- **backend**: Ajouter liste étudiants paginée avec IP WAN et VNI
  ([`4d5f708`](https://github.com/SimonLou-Dev/labomatics/commit/4d5f70876b7409d24f1e3deef56bf1cc0516d474))

- StudentService + DTO pour la liste paginée avec pagination - Route GET /v1/students?page=size
  retourne étudiants avec cohort + IP WAN + VNI - StudentRepository.list_with_pagination() avec
  jointures SQL optimisées - Réparer relationships cassées: IpAllocation et VxlanAllocation -
  Enlever back_populates cassés dans IpRange et VxlanRange

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **backend**: Api routes for cluster and range management
  ([`828c89a`](https://github.com/SimonLou-Dev/labomatics/commit/828c89a82182555cd4cf99f73e294b045a064024))

- Add GET/POST/PATCH/DELETE routes for clusters with pagination - Add routes for credential
  management and Proxmox connection testing - Add routes for attaching/detaching IP ranges and VXLAN
  ranges - Add routes for cluster config upload and application - Add GET/POST/PATCH/DELETE routes
  for IP ranges and VXLAN ranges - All list endpoints return paginated responses - Secure mutations
  with manage_cluster role requirement

- **backend**: Bootstrap cluster config and RBAC for admin
  ([`db399cc`](https://github.com/SimonLou-Dev/labomatics/commit/db399cc9785b198a7c670c3f09b865faee7d19d1))

- Add cluster config bootstrap at startup (idempotent, one-shot) - Add manage_cluster role for
  administrative operations - Register new services (Cluster, IpRange, VxlanRange, ClusterConfig) as
  dependencies - Services auto-wire to repositories and other dependencies

- **backend**: Implémenter auth, RBAC, student import, mail service
  ([`4929261`](https://github.com/SimonLou-Dev/labomatics/commit/4929261855722e01f16756cf177673c13af9304d))

- JWT authentication + role-based access control (RBAC) - AuthService: decode token, ensure role,
  exchange code for token - StudentImportService: preview/apply CSV import avec validation -
  MailService: stub avec TODO pour SMTP réel - KeycloakAdminConnector: create/delete user, manage
  groups/roles - DTO: AuthUser, MeDTO, StudentImportMapping, StudentImportDiff - Middlewares: JWT
  verification et role extraction - Routes: /me, /students/import/preview, /students/import/apply -
  Settings: KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD - Alembic migrations initiales

Fixes #17, #24, #19, #20, #21

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **backend**: Vxlan MTU migration and cluster bootstrap configuration
  ([`2835af9`](https://github.com/SimonLou-Dev/labomatics/commit/2835af90039f7002bcb0d7d1f710918c01942119))

- Add Alembic migration to add mtu field to vxlan_range table (default 1350) - Add
  clusterconfig.example.yaml template for cluster bootstrap - Include example configuration for
  clusters, IP ranges, and VXLAN ranges - Template ready for deployment with CLUSTER_CONFIG_PATH
  environment variable

- **backend/frontend**: Student import complet + filtrage + cohort/cluster assign
  ([`e19ff3f`](https://github.com/SimonLou-Dev/labomatics/commit/e19ff3fc4ad8f0089371c732a92408848e86d562))

- StudentService: create/update/delete avec Keycloak + password + mail - Login auto:
  firstname.lastname (non-modifiable) - Cohort/Enrollment idempotent + année scolaire 01/09-31/08 -
  User ajouté groupe 'student' automatiquement - Cohort assigné au cluster par défaut - Frontend:
  tri par nom, filtrage par promo, recherche globale (nom/email/IP) - Recherche backend sur tous les
  étudiants, pas juste la page actuelle - Enrollment actif détecté par dates, pas end_date is None -
  Eager load relations pour éviter DetachedInstanceError

- **cli**: Ajouter compte technique keycloak + permissions realm-management
  ([`f83929c`](https://github.com/SimonLou-Dev/labomatics/commit/f83929c0f73b58cb098793d02fd5fe9838d174d5))

- Creation user labomatics-admin (password non-temporaire) - Assignment des 4 rôles
  realm-management: manage-users, view-users, manage-clients, view-clients - Methodes
  KeycloakClient: get_client_uuid, assign_client_role_to_user - Affichage credentials en fin
  d'install (username + password en couleur) - Role manage_user assigné au groupe superadmin

Fixes #17, #24

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **cli**: Scaffold v0.4 avec commande install + cloud-init Alpine
  ([`dee7eba`](https://github.com/SimonLou-Dev/labomatics/commit/dee7eba25496fdb766084a3b945a97b16234fcf6))

- **cli**: Update schema and keycloak setup for admin roles
  ([`aebc43c`](https://github.com/SimonLou-Dev/labomatics/commit/aebc43c46a1f16636541b5762ce2451f4360c3fa))

- Update VnetConfig with vni_min, vni_max fields - Update ClusterEntry with sdn_zone, token_id,
  token_secret fields - Update ConfigGenerator to pass these fields to templates - Add
  manage_cluster role creation in keycloak setup - Assign manage_cluster role to superadmin group -
  Add user existence check before creating new users

- **db**: Modèle de données SQLAlchemy v0.4-v0.5
  ([`449b7fb`](https://github.com/SimonLou-Dev/labomatics/commit/449b7fb103e38021ca0ef0d4018b23e386b6e805))

- 16 modèles SQLAlchemy: 6 identité, 2 sécurité, 8 provisioning - 16 repositories avec pattern
  générique BaseRepository - Migrations Alembic: identité, sécurité, provisioning multi-cluster -
  Index uniques partiels pour historique (enrollment, allocations) - Chiffrement Fernet pour secrets
  cluster

Resolves #16

- **frontend**: Add Lab page placeholder
  ([`4a94e89`](https://github.com/SimonLou-Dev/labomatics/commit/4a94e895955e0f98dddfd2c0b0a4292e435b9bfb))

- Add Lab.vue page for individual student lab details - Accessible at /lab/:userId route -
  Placeholder for future integration with lab provisioning data

- **frontend**: Admin pages for cluster and range management
  ([`d2d550b`](https://github.com/SimonLou-Dev/labomatics/commit/d2d550b7edfd1d19c8b944f77e4b4d69bc61f36b))

- Add Clusters.vue with DataTable CRUD, credential management, range attachment - Add WanRanges.vue
  with IP range management and utilization progress bars - Add NetworkRanges.vue with VXLAN range
  management and utilization progress bars - Add WanRangeDetails.vue showing IP allocations with
  student info and links - Add NetworkRangeDetails.vue showing VNI allocations with student info -
  Add test connection button with Proxmox credentials verification - Add navigation to detail pages
  from management dialogs - Progress bars use orange color with border for visibility

- **frontend**: Api clients and types for cluster management
  ([`08316a7`](https://github.com/SimonLou-Dev/labomatics/commit/08316a7f012f56148bd63654ac663336410c82ac))

- Add clusters.ts with CRUD operations, credential, range attachment, config upload - Add
  ipRanges.ts with CRUD and allocation retrieval - Add vxlanRanges.ts with CRUD and allocation
  retrieval - Add type definitions for all DTOs (ClusterDTO, IpRangeDTO, VxlanRangeDTO) - Add type
  definitions for credentials and allocations - All list operations support pagination

- **frontend**: Créer interface utilisateur complète avec primevue
  ([`5d7a851`](https://github.com/SimonLou-Dev/labomatics/commit/5d7a8512418728d71730e5118eebd93903d232a0))

- Layout responsive: SidebarLayout, MainLayout avec navigation par rôle - Pages: Login (minimal),
  Dashboard (palette couleurs), Students (empty) - Theme system: light/dark/dyslexia modes avec
  localStorage persistence - Design system: couleur primaire orange (#FF6B00), surface steel - CSS
  variables RGB-space et Tailwind primary-lab/error-lab palette - PrimeVue Aura preset configuré
  avec custom theming - PrimeUI Community License management (.env.local) - Composables: useTheme
  (dark/dyslexia), useSidebar - Assets: logo.svg, logo-large.svg

Fixes #18

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **frontend**: Routes and global components for admin UI
  ([`3af904b`](https://github.com/SimonLou-Dev/labomatics/commit/3af904bb4f3c453e5f4efcc52840c89bf64a4d5f))

- Add routes for /admin/cluster, /admin/wan, /admin/networks, /lab/:userId - Add routes for
  WanRangeDetails and NetworkRangeDetails with :rangeId param - Mount Toast and ConfirmDialog
  components globally for notifications - Add breadcrumb navigation in MainLayout - Export new API
  clients and types from index files

- **frontend**: Tableau Students avec pagination backend et coloration cohort
  ([`4a6d907`](https://github.com/SimonLou-Dev/labomatics/commit/4a6d9074a6ac19a37a738e416f9dbf234ecef300))

- Service API pour récupérer liste paginée des étudiants du backend - Refactor Students.vue:
  DataTable paginée + colonnes IP WAN + VNI - Utility getCohortColor() pour colorer badges cohort de
  manière stable (hash) - Ajout credentials: 'include' pour envoyer cookies auth avec requête -
  Colonnes: ID | Login | Nom | Email | Promo (badge) | IP WAN | VNI | Actions

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- **install**: Cli v0.4 complet + cloud-init + setup Keycloak + OIDC
  ([`80f2dc1`](https://github.com/SimonLou-Dev/labomatics/commit/80f2dc1c457be83c98dc71dd512b0db87e32d180))

- **install**: Implémentation complète - Proxmox API + SSH upload + verification + error handling
  ([`fc369e7`](https://github.com/SimonLou-Dev/labomatics/commit/fc369e7d39d3261927b96accdabc28658db91e3e))

### Refactoring

- Cleanup and improve Proxmox helper clients
  ([`4761893`](https://github.com/SimonLou-Dev/labomatics/commit/47618930d7e6b07da99a7334be0296f23112bec8))

- Remove unused import (re) from _root.py - Use contextlib.suppress for error handling in ACL client
  - Fix error messages to use actual userid variable - Add proper docstrings and error handling

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>

- Exports et types API range (aucun changement de logique)
  ([`f99c9de`](https://github.com/SimonLou-Dev/labomatics/commit/f99c9deeaa93b51a7650836a9236989851417e32))

- Simplifie detail pages et ranges list, utilise GET /id au lieu de lister
  ([`369bed5`](https://github.com/SimonLou-Dev/labomatics/commit/369bed54e2aaa2f25a1c57b29726bfe7903d878c))

Frontend: - WanRangeDetails, NetworkRangeDetails: utilise getIpRange(id) / getVxlanRange(id) au lieu
  de lister tout et chercher - Clusters.vue: corrigé nom champ 'storage' -> 'default_storage' dans
  formData - WanRanges, NetworkRanges: remplacé ProgressBar slot template (inexistant) par div avec
  linear gradient pour affichage du %

- **backend**: Use generic pagination and fix repository patterns
  ([`c50bcd3`](https://github.com/SimonLou-Dev/labomatics/commit/c50bcd3012cef7e3dc1adadc6025ff6fec9c184a))

- Use BaseRepository.paginate() with relations for StudentService - Remove
  StudentRepository.list_with_pagination (replaced by generic paginate) - Add order_by support to
  BaseRepository.paginate() - Add IntegrityError handling to BaseRepository.delete() returning 409 -
  Normalize IP allocation filters for consistency - Student pagination now uses generic selectinload
  for relations

- **frontend**: Standardize student API to use http client
  ([`5a2727b`](https://github.com/SimonLou-Dev/labomatics/commit/5a2727b59fd35e97602fe7bc9702ebf1df0f8b04))

- Add listStudents() returning PaginatedResponse<StudentListItem> - Add StudentListItem interface
  for list responses - Use http.ts client instead of direct fetch - Maintain pagination fields
  (page, per_page, total, total_pages) - Follow consistent API naming conventions across all domains

- **monorepo**: Déplacer labomatics/ → old_cli/labomatics/ pour v0.4
  ([`10aa56c`](https://github.com/SimonLou-Dev/labomatics/commit/10aa56c8fccf4f6935dede9d39ded31a0c4d66e3))

- **monorepo**: Pyproject.toml → old_cli/, supprimer systemd/
  ([`6ed9723`](https://github.com/SimonLou-Dev/labomatics/commit/6ed972322d0bf57d6c4a84e862ba006c9465745b))


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

# TLS, CA et audience Keycloak

> **Audience** : administrateur du lab Proxmox.

Ce document explique l'architecture de confiance TLS mise en place sur la branche
`feat/security`, les pièges rencontrés, et comment débloquer une install existante.

---

## Deux CA indépendantes

Le backend parle à deux services distincts en HTTPS, chacun avec sa propre CA :

| Service                  | CA                                             | Portée                     |
|---------------------------|------------------------------------------------|-----------------------------|
| Keycloak / Traefik        | CA interne Labomatics (`/etc/labomatics/certs/ca.crt`) | Globale, une par install   |
| Proxmox (API `:8006`)     | CA du cluster Proxmox (`/etc/pve/pve-root-ca.pem`)     | Une par cluster Proxmox    |

Ce sont deux CA **totalement indépendantes**, générées par deux systèmes différents.
Un `CA_BUNDLE` global unique ne peut donc pas valider les deux : le backend stocke la
CA Proxmox **par cluster** (table `cluster_credential`, colonne `ca_cert`), pas dans
`CA_BUNDLE`.

Proxmox VE partage `/etc/pve/` entre tous les nœuds d'un même cluster (pmxcfs) : un
seul nœud suffit pour récupérer la CA, valable pour tout le cluster.

---

## CA interne Labomatics (Keycloak / Traefik)

Générée par le CLI (`stack/init/generate-certs.sh.j2`) au premier `labomatics install`,
déposée dans `/etc/labomatics/certs/`. Le backend la reçoit via :

```
CA_BUNDLE=/etc/labomatics/certs/ca.crt
ENVIRONMENT=production
```

(`cli/labomatics_cli/templates/stack/env/backend.env.j2`), avec le fichier monté dans
les conteneurs `api`/`worker` (`docker-compose.yml.j2`).

### Piège : OpenSSL 3.x / Python 3.13 rejette les CA sans `keyUsage`

Une CA auto-signée générée par un simple `openssl req -x509` (sans extensions) était
acceptée par OpenSSL 1.1.1, mais Python 3.13 active par défaut
`ssl.VERIFY_X509_STRICT`, qui applique la RFC 5280 : une CA utilisée comme ancre de
confiance doit porter explicitement `keyUsage` avec `keyCertSign`. Sans ça :

```
SSLCertVerificationError: certificate verify failed: CA cert does not include
key usage extension
```

Fix (déjà appliqué dans `generate-certs.sh.j2`) :

```bash
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj '/CN=labomatics-ca' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
```

> Ce fix ne s'applique qu'aux **nouvelles** CA. Une CA déjà générée (`ca.crt`/`ca.key`
> déjà présents sur la VM) est conservée telle quelle par le script — il faut la
> supprimer sur la VM pour forcer sa régénération (ce qui régénère aussi tous les
> certs serveur signés par elle, et nécessite de re-propager la CA sur les nœuds
> Proxmox via la tâche `ca_propagation`).

---

## CA par cluster Proxmox

Chaque cluster Proxmox a sa propre CA auto-signée (`/etc/pve/pve-root-ca.pem`),
indépendante de la CA Labomatics. Stockée en clair (donnée publique, pas un secret)
dans `cluster_credential.ca_cert`.

- **À l'install** : `BackendTask._proxmox_ca` (CLI) récupère `pve-root-ca.pem` via SSH
  sur un nœud et l'injecte dans `clusterconfig.yaml` ; le backend la charge au
  bootstrap (`ClusterConfigService.apply`).
- **Depuis le front** : page admin *Clusters* → bouton credential → champ
  « CA du cluster Proxmox » (textarea, coller le contenu de `pve-root-ca.pem`).
  Laisser vide lors d'une rotation de token **ne l'efface pas** — elle est préservée
  si le formulaire n'en envoie pas de nouvelle (`ClusterService.set_credential`).
- **Résolution runtime** : `labomatics/core/security/tls.py::resolve_verify` écrit la
  CA sur disque (cache par hash de contenu) et la passe en `verify=` à `httpx`/
  `requests`/`proxmoxer` ; sans CA de cluster, retombe sur `CA_BUNDLE` global.

Si un cluster n'a pas sa CA configurée, les appels vers son API Proxmox échoueront la
vérification TLS une fois `CA_BUNDLE`/`ENVIRONMENT=production` activés.

---

## Audience Keycloak (`aud`)

Keycloak met par défaut `aud: ["account"]` sur les access tokens — **pas** le
`client_id` du client (`labomatics`), sauf mapper d'audience dédié. Le backend vérifie
`aud` (`AuthService.authenticate`), d'où :

```
jwt.exceptions.InvalidAudienceError: Audience doesn't match
```

### Fix définitif (CLI)

`KeycloakTask._client` (CLI) ajoute maintenant un mapper d'audience au client
`labomatics` via `KeycloakApi.ensure_audience_mapper` — idempotent, appliqué à chaque
install/réinstall.

### Débloquer une install existante sans réinstaller

Console admin Keycloak :

1. **Clients** → `labomatics`
2. Onglet **Client scopes** → `labomatics-dedicated`
3. **Add mapper** → **By configuration** → **Audience**
4. `Included Client Audience = labomatics`, `Add to access token = ON`,
   `Add to ID token = OFF`
5. **Save**, puis se reconnecter (les tokens déjà émis restent invalides jusqu'au
   prochain login).

---

## Checklist après mise à jour d'un cluster existant

- [ ] CA interne régénérée avec `keyUsage` si le cluster a été installé avant ce fix
- [ ] `ca_cert` renseigné pour chaque cluster Proxmox (front ou `clusterconfig.yaml`)
- [ ] Mapper d'audience ajouté sur le client `labomatics` dans Keycloak
- [ ] `ENVIRONMENT=production` + `CA_BUNDLE` présents dans `backend.env`

# Contribuer à labomatics

## Branches

| Branche | Rôle |
|---|---|
| `main` | Production — protégée, merge uniquement via PR validée |
| `dev` | Branche d'intégration — base de toutes les PR |
| `feature/*` | Nouvelles fonctionnalités |
| `fix/*` | Corrections de bugs |
| `docs/*` | Documentation uniquement |

Workflow : `feature/xxx` → PR → `dev` → PR → `main`

## Développement

```bash
git clone https://github.com/esgilabs/labomatics-cli
cd labomatics-cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Avant de soumettre une PR

```bash
ruff check labomatics/          # lint
ruff format labomatics/         # formatage
mypy labomatics/                # typage
pytest tests/ -v                # tests
```

La CI vérifie automatiquement ces étapes sur chaque PR.

## Conventional Commits

Les messages de commit suivent la convention [Conventional Commits](https://www.conventionalcommits.org/).
Semantic-release les analyse automatiquement pour déterminer le bump de version et générer le changelog.

| Préfixe | Effet | Exemple |
|---|---|---|
| `feat:` | bump **minor** (0.x.0) | `feat: ajouter commande recreate` |
| `fix:` | bump **patch** (0.0.x) | `fix: corriger allocation IP WAN` |
| `perf:` | bump **patch** | `perf: réduire les appels API Proxmox` |
| `feat!:` ou `BREAKING CHANGE:` | bump **major** (x.0.0) | `feat!: nouveau format infra.yaml v2` |
| `docs:` | aucun bump | `docs: mettre à jour le README` |
| `chore:` | aucun bump | `chore: mettre à jour les dépendances` |
| `refactor:` | aucun bump | `refactor: extraire ip_pool.py` |
| `test:` | aucun bump | `test: ajouter tests config` |
| `ci:` | aucun bump | `ci: ajouter job release` |

Format complet :
```
<type>(<scope optionnel>): <description courte>

<corps optionnel>

BREAKING CHANGE: <description si breaking>
```

Exemples :
```
feat(deploy): support du clone cross-node avec target=

fix(ip_pool): corriger le parsing des ranges d'exclusion IP

feat!: remplacer wan_subnet/wan_gateway par wan_pool dans infra.yaml

BREAKING CHANGE: le format infra.yaml v1 n'est plus supporté
```

## Standards

- **Typage** : annotations de type sur toutes les fonctions publiques
- **Tests** : tout nouveau module doit avoir des tests unitaires dans `tests/`
- **Commits** : respecter le format Conventional Commits (requis pour semantic-release)
- **Secrets** : ne jamais committer `.env`, `credentials.csv` ou tout fichier contenant des mots de passe

## Signaler un bug

Ouvrir une issue GitHub avec :
- La commande exacte exécutée
- Le message d'erreur complet
- La version (`pip show labomatics`)
- La version Proxmox VE

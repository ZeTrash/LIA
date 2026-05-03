# Structure et organisation du workspace LIA

## Vue d'ensemble de la structure

```
LIA/
├── README.md                    # Documentation principale du projet
├── .gitignore                   # Exclusions Git (fichiers sensibles, DB, etc.)
├── env.example                  # Template de configuration environnement
│
├── config/                      # Fichiers de configuration
│   ├── api.conf.example         # Template configuration API
│   └── api.conf                 # Configuration réelle (non versionnée)
│
├── docs/                        # Documentation générale
│   ├── architecture.md          # Architecture technique du système
│   ├── CONTEXT.md               # Contexte et vision du projet
│   └── STRUCTURE.md             # Ce fichier
│
├── charge_timeline/             # Planification et cahiers des charges
│   ├── etape1_cahier_charges/   # Étape 1 : Infrastructure mémoire
│   │   ├── README.md            # Cahier des charges détaillé
│   │   └── livrables/           # Livrables de l'étape 1
│   │       ├── api_spec_openapi.yaml
│   │       ├── architecture_persistance.md
│   │       ├── gouvernance_algorithmes.md
│   │       ├── plan_tests_observabilite.md
│   │       ├── schema_memory_context.json
│   │       ├── schema_memory_context.sql
│   │       ├── validation_SL1_SL4.md
│   │       └── mock_server/     # Serveur mock pour tests
│   │
│   ├── etape2_simulation_multiagent/  # Étape 2 : Simulation multi-agent
│   │   └── README.md
│   │
│   └── etape3_interface_supervision/  # Étape 3 : Interface supervision
│       └── README.md
│
└── memory_service/              # Service mémoire (implémentation Étape 1)
    ├── README.md                # Documentation du service
    ├── requirements.txt         # Dépendances Python
    ├── src/
    │   └── memory_service/      # Code source
    │       ├── __init__.py
    │       ├── api.py           # Endpoints FastAPI
    │       ├── cli.py           # Interface ligne de commande
    │       ├── config.py        # Configuration
    │       ├── db.py            # Accès base de données
    │       ├── main.py          # Point d'entrée
    │       ├── metrics.py       # Métriques et observabilité
    │       ├── models.py        # Modèles SQLAlchemy
    │       ├── schemas.py       # Schémas Pydantic
    │       └── store.py         # Logique métier
    ├── tests/                   # Tests unitaires et d'intégration
    │   ├── test_api.py
    │   └── test_cli.py
    └── data/                     # Données (non versionnées)
        ├── memory.db            # Base de données SQLite
        └── seed_memories.json   # Données de seed
```

## Principes d'organisation

### Séparation des préoccupations

- **Documentation** : Centralisée dans `docs/` et `charge_timeline/`
- **Code source** : Dans `memory_service/src/`
- **Configuration** : Dans `config/` (fichiers réels non versionnés)
- **Tests** : À côté du code source dans `memory_service/tests/`
- **Données** : Dans `memory_service/data/` (non versionnées)

### Gestion des fichiers sensibles

⚠️ **Important** : Les fichiers suivants ne doivent JAMAIS être versionnés :

- `config/api.conf` (contient les clés API)
- `.env` (variables d'environnement)
- `memory_service/data/*.db` (bases de données)
- Tous les fichiers contenant des secrets

Utiliser les fichiers `.example` comme templates.

### Structure modulaire

Chaque étape du projet a son propre dossier dans `charge_timeline/` :
- Documentation et cahier des charges
- Livrables et spécifications
- Code source (si applicable)

### Évolutivité

La structure est conçue pour accueillir facilement :
- De nouvelles étapes dans `charge_timeline/`
- De nouveaux services (similaire à `memory_service/`)
- De nouvelles documentations dans `docs/`

## Conventions de nommage

### Fichiers et dossiers

- **README.md** : Présent dans chaque dossier important
- **Snake_case** : Pour les fichiers Python
- **kebab-case** : Pour les dossiers et fichiers de configuration
- **UPPER_CASE** : Pour les variables d'environnement

### Documentation

- **Markdown** : Format standard pour toute la documentation
- **YAML** : Pour les spécifications API (OpenAPI)
- **JSON** : Pour les schémas de données

## Maintenance

### Ajout d'une nouvelle étape

1. Créer le dossier dans `charge_timeline/etapeN_nom/`
2. Ajouter un `README.md` avec le cahier des charges
3. Créer un dossier `livrables/` si nécessaire
4. Mettre à jour le `README.md` principal

### Ajout d'un nouveau service

1. Créer un dossier à la racine (ex: `new_service/`)
2. Suivre la structure de `memory_service/` comme modèle
3. Ajouter la documentation dans `docs/`
4. Mettre à jour le `README.md` principal

### Modification de la structure

Toute modification importante de la structure doit être :
1. Documentée dans ce fichier
2. Réfléchie pour maintenir la cohérence
3. Communiquée dans le `README.md` principal




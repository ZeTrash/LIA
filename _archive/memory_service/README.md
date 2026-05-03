# Memory Service – Étape 1

Service FastAPI local implémentant la couche mémoire persistante décrite dans le cahier des charges de l’étape 1.

## Structure

```
memory_service/
├── requirements.txt
├── src/memory_service/
│   ├── api.py            # Endpoints FastAPI
│   ├── config.py         # Paramètres (TTL, seuils, etc.)
│   ├── store.py          # Logique métier + stockage en mémoire
│   ├── schemas.py        # Modèles Pydantic
│   └── main.py           # Point d’entrée uvicorn
└── tests/test_api.py     # Tests fumée
```

## Installation

```bash
cd memory_service
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Lancer le serveur

```bash
uvicorn memory_service.api:create_app --factory --reload
# ou
python -m memory_service.main
```

Endpoints principaux :

- `GET /context` – assemble traits, objectifs et souvenirs (latence <200 ms, <10 KB).
- `POST /interaction` – journalise une interaction et crée un souvenir optionnel.
- `POST /trait-update` – versionne un trait avec verrou optimiste.
- `POST /governance/check` – applique les garde-fous (dérive, cohérence, volume).
- `GET /metrics` – expose les KPI d’observabilité.
- `GET /metrics/prom` – export Prometheus (histogrammes latence/payload, compteurs interactions/garde-fous).

## Configuration

Paramètres modifiables via variables d’environnement `MEMORY_SERVICE_*` ou fichier `.env` (voir `config.py`) :

- `TTL_CONFIG` (jours par catégorie),
- seuils `GOVERNANCE_THRESHOLD_WARN/BLOCK`,
- limites `MAX_MEMORIES`, `CONTEXT_PAYLOAD_*`.

## Tests

### Tests unitaires
```bash
pytest tests/test_api.py tests/test_cli.py
```

### Tests d'intégration
```bash
# Tous les tests d'intégration
pytest tests/test_integration.py -v

# Script de validation complet
python scripts/validate_integration.py
```

Les tests d'intégration valident :
- Conformité aux spécifications OpenAPI
- Latence < 200ms et payload < 10KB
- Idempotence, versioning, détection de doublons
- Performance et cohérence des données

Voir `tests/README_INTEGRATION.md` pour plus de détails.

## Seed & supervision CLI

- `python -m memory_service.cli seed [-f chemin.json]` : injecte les données du fichier (`data/seed_memories.json` par défaut) via SQLAlchemy.
- `python -m memory_service.cli stats [--session-id X]` : affiche les compteurs (traits, souvenirs, interactions) et les objectifs actifs.
- `python -m memory_service.cli metrics` : imprime les KPI calculés (latence, couverture traits, dérives, etc.).

Le module `memory_service.cli` est couvert par `tests/test_cli.py` afin de garantir qu’un seed minimal fonctionne même sur une base vierge.




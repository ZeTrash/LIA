# Architecture technique & persistance cible

## 1. Vue d’ensemble
- Service unique `memory-service` (FastAPI ou équivalent) exposant l’API locale.
- Stockage principal : **SQLite 3** (fichier `data/memory.db`) avec WAL activé pour supporter 2 à 4 écritures concurrentes.
- Archives & exports : fichiers JSON Lines compressés (`.jsonl.zst`) sous `archives/` pour InteractionLog et souvenirs purgés.
- Configuration dynamique (`governance_params`, poids, TTL) stockée en JSON (`config/governance.json`) + table SQL pour versionning.

## 2. Choix de persistance

| Besoin | Solution | Justification |
| --- | --- | --- |
| Transactions rapides locales | SQLite + WAL | ACID, zéro dépendance serveur, outils familiers |
| Requêtes top-K | Index composites `(category, importance_score DESC)` | Sélection rapide pour contexte |
| Historisation traits | Table `trait_versions` + deltas JSON | Rollback rapide et audit |
| Logs massifs | JSONL gzip/zstd + rotation 2 Go | Économie d’espace, export ML |

## 3. Structure des fichiers
```
charge_timeline/etape1_cahier_charges/
└── livrables/
    ├── schema_memory_context.json
    ├── schema_memory_context.sql
    ├── api_spec_openapi.yaml
    ├── architecture_persistance.md
    ├── gouvernance_algorithmes.md
    └── plan_tests_observabilite.md
```

## 4. Gestion des historiques
- `InteractionLog` : table active + export quotidien `archives/interactions/YYYY/MM/DD.jsonl.zst` (retention 90 jours).
- `Souvenir` : quand purgé, copie JSON minimal (`memory_id`, `category`, `content`, scores) stockée dans le fichier d’archive du jour.
- Compression : `zstd -T0 -9` (script automatisé). Index manifest `archives/index.json` avec taille, checksum.

## 5. Index & performances
- `traits(trait_id)` + `traits(trait_id, version)` pour lectures rapides.
- `souvenirs(category, importance_score DESC)` et `souvenirs(tags)` pour filtrage.
- `interaction_logs(session_id, occurred_at DESC)` pour audit session.
- `request_audit(endpoint, created_at DESC)` pour observabilité API.
- `PRAGMA cache_size = -8000` (≈8 Mo) pour optimiser lectures `GET /context`.

## 6. TTL dynamiques
- Valeurs par défaut (préférence 180 j, faits 45 j, alertes 15 j) stockées dans `governance_params`.
- TTL par souvenir modifiable par `POST /interaction` via `decisions.ttl_override_days`.
- Job `housekeeping.py` applique TTL + recalcul `S(memory)` pour décider purge (cf. `gouvernance_algorithmes.md`).

## 7. Sécurité & droits
- API protégée par header `X-LIA-Token` (token long 64 caractères) + liste blanche d’origines (boucle locale par défaut).
- Rôles :
  - `llm_agent` : accès `/context`, `/interaction`.
  - `supervisor` : accès complet + `/metrics` CSV.
  - `governance` : exécution `POST /governance/check` et rollback.
- Audit : table `request_audit` + export hebdo CSV (`exports/audit_YYYYWW.csv`).

## 8. Versioning & packaging
- Chaque build taggé `context_version = YYYY.MM.DD-XX`.
- `schema_memory_context.json` versionné dans Git + livré avec service (validation runtime via `jsonschema`).
- Migration SQL gérée par `alembic` ou script custom (`scripts/migrate.py`).

## 9. Dépendances externes
- Aucun service distant requis à l’étape 1.
- Options futures : brancher Prometheus (`/metrics/prom`) et stockage objet pour archives.

Cette architecture est conçue pour être implémentée rapidement en local puis étendue (Étape 2) sans refonte majeure.





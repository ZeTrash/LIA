# Plan de tests automatisés & Observabilité

## 1. Objectifs
- Vérifier que la mémoire locale respecte les SLA (latence, taille contexte).
- Garantir l’intégrité des règles de gouvernance (scoring, drift, purge).
- Offrir une visibilité temps réel via un dashboard minimal et exports (JSON/CSV/Prometheus).

## 2. Environnements & outillage

| Environnement | Usage | Outillage | Déclenchement |
| --- | --- | --- | --- |
| `local-dev` | Dév & debug | `pytest`, sqlite en mémoire, `uvicorn` | Manuel à chaque feature |
| `ci-smoke` | Validation continue | GitHub Actions, `pytest -m "not slow"`, `newman`, `k6 smoke` | À chaque PR |
| `ci-load` | Charge ponctuelle | `k6` (200 req/s), `sqlite` WAL, `locust` optionnel | Nuit + avant release |
| `chaos-lab` | Résilience | Scripts PowerShell (coupure fichier, latence réseau), `toxiproxy` | Mensuel |

## 3. Cas de tests prioritaires

### 3.1 Schéma & données
- Validation JSON Schema (`ajv-cli test schema_memory_context.json mock-data/context*.json`).
- Tests migration SQL (`pytest tests/test_migrations.py`).
- Injection de doublons (`hash` identique) → vérifier incrément fréquence.

### 3.2 API contractuelle
- Collection Postman `collections/memory.postman_collection.json` (happy path + erreurs) exécutée via `newman`.
- Vérifier `GET /context` < 200 ms (k6 script `scripts/get-context.js`).
- Idempotence `POST /interaction` (même `interaction_id`).
- Conflit `POST /trait-update` (version mismatch) renvoie 409 + payload correct.

### 3.3 Gouvernance & scoring
- Scénario dérive ton agressif → `verdict = block` + rollback trait.
- TTL expiré + score faible → purge dans l’heure.
- Signal `conflict_set` déclenche alerte.

### 3.4 Observabilité
- Export CSV : `GET /metrics?format=csv` → fichier non vide, colonnes `timestamp,kpi,value`.
- Endpoint Prometheus (`/metrics/prom`) s’intègre dans `promtool check metrics`.
- Dashboard CLI (`scripts/dashboard_cli.py`) affiche KPI avec codes couleur.

### 3.5 Résilience
- Indisponibilité store (renommer fichier SQLite) → `GET /context` retourne 503 + `error_code=STORE_DOWN`.
- Corruption intentionnelle (supprimer ligne `trait`) → script de cohérence doit détecter et marquer `status=deprecated`.

## 4. Dashboard & KPI

| KPI | Source | Seuil alerte | Rendu |
| --- | --- | --- | --- |
| `latency_context_ms` | middleware FastAPI | >180 ms | Gauge + sparkline |
| `context_payload_bytes` | réponse `/context` | >9 KB | Histogramme |
| `coverage_traits_pct` | calcul batch | <60 % | Gauge |
| `coherence_score` | POST /interaction | <0.85 | Line chart |
| `drift_alerts_count` | gouvernance | ≥3/100 interactions | Counter + alert Slack |
| `ttl_purge_rate` | job purge | >25 % | Bar chart |
| `store_availability` | healthcheck | <99.5 % | Status badge |

Dashboard minimal : script CLI (curseur `rich`) + dashboard Grafana (JSON `dashboards/lia-memory.json`).

## 5. Observabilité technique
- Logging structuré JSON (`logger.info("interaction_stored", {...})`).
- Traces OpenTelemetry exportées en OTLP HTTP (optionnel) pour suivre latence endpoints.
- Alertes Slack/Email via `alertmanager` (drift blocant, purge >30 %, indisponibilité >60 s).

## 6. Critères d’acceptation tests
- 100 % des tests `pytest` + `newman` verts.
- `k6` : P95 `GET /context` < 210 ms, erreurs <1 %.
- Tests chaos : service se rétablit <30 s avec logs d’erreur interprétables.
- Dashboard accessible et mis à jour <15 s.

## 7. Scripts à livrer
- `scripts/run_tests.ps1` : orchestre pytest + newman + k6 smoke.
- `scripts/seed_demo_data.py` : génère traits/souvenirs de démonstration.
- `scripts/dashboard_cli.py` : viewer CLI KPIs.

Ces scripts seront ajoutés dans l’étape d’industrialisation mais la description est ici pour validation fonctionnelle.





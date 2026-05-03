# Tests d'intégration - Service Mémoire

## Vue d'ensemble

Les tests d'intégration valident que le service mémoire est conforme aux spécifications OpenAPI et fonctionne correctement en conditions réelles.

## Structure des tests

### `test_integration.py`
Tests de conformité des contrats API :
- **TestAPIContract** : Validation des schémas, latence, taille payload
- **TestDataConsistency** : Cohérence des données (contexte après interaction, versioning, doublons)
- **TestPerformance** : Tests de performance et limites

### `test_mock_comparison.py`
Comparaison avec le mock server (si disponible) :
- Structure des réponses
- Cohérence avec les payloads d'exemple

## Exécution

### Tous les tests d'intégration
```bash
pytest tests/test_integration.py -v
```

### Tests spécifiques
```bash
# Tests de contrat API uniquement
pytest tests/test_integration.py::TestAPIContract -v

# Tests de cohérence des données
pytest tests/test_integration.py::TestDataConsistency -v

# Tests de performance
pytest tests/test_integration.py::TestPerformance -v
```

### Script de validation
```bash
python scripts/validate_integration.py
```

## Critères de validation

### GET /context
- ✅ Latence < 200ms
- ✅ Payload < 10KB
- ✅ Tous les champs requis présents
- ✅ `trace_id` et `context_checksum` générés

### POST /interaction
- ✅ Idempotence via `interaction_id`
- ✅ Tous les champs requis présents
- ✅ `severity` calculé correctement
- ✅ Souvenir créé si `decisions.create_memory=True`

### POST /trait-update
- ✅ `delta` accepté comme objet
- ✅ `version_token` retourné
- ✅ Versioning incrémental
- ✅ Gestion des conflits de version

### POST /governance/check
- ✅ `signals` accepté comme array
- ✅ Drift bloquant → `verdict=block`
- ✅ Drift modéré → `verdict=warn`
- ✅ Issues avec `code` et `severity`

### GET /metrics
- ✅ Tous les KPI présents
- ✅ Endpoint Prometheus fonctionnel

## Résultats attendus

Tous les tests doivent passer pour valider l'intégration :
- ✅ Conformité aux spécifications OpenAPI
- ✅ Respect des SLA (latence, taille)
- ✅ Cohérence des données
- ✅ Performance acceptable

## Comparaison avec mock server

Pour comparer avec le mock server, démarrer d'abord le mock :
```bash
cd charge_timeline/etape1_cahier_charges/livrables/mock_server
uvicorn mock_server.server:app --port 4600
```

Puis exécuter les tests de comparaison :
```bash
pytest tests/test_mock_comparison.py -v
```




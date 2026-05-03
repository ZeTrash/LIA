# Plan de tests et validation – Étape 2.5

## Objectifs

Valider que `LocalLLMAdapter` fonctionne correctement, génère des réponses cohérentes avec la personnalité de LIA, et gère les erreurs avec fallback.

## Environnements de test

| Environnement | Usage | Outillage | Déclenchement |
| --- | --- | --- | --- |
| `local-dev` | Tests unitaires et d'intégration | `pytest`, `transformers`, `torch` | À chaque modification |
| `ci-smoke` | Validation continue | GitHub Actions, `pytest -m "not slow"` | À chaque PR |
| `ci-integration` | Tests d'intégration complets | `pytest`, `memory_service` + LocalLLMAdapter | Nuit |
| `performance` | Tests de performance | Benchmarks latence/mémoire | Avant release |

## Scénarios de test

### 1. Test basique – Chargement et génération

**Objectif** : Vérifier que le modèle peut être chargé et générer des réponses.

**Étapes** :
1. Créer instance `LocalLLMAdapter`
2. Charger modèle GPT-2 Small
3. Générer réponse simple (sans contexte)
4. Vérifier que la réponse est générée

**Critères de validation** :
- ✅ Modèle chargé sans erreur
- ✅ Réponse générée (non vide)
- ✅ Latence < 5 secondes (premier chargement)
- ✅ Mémoire < 200 MB (quantisé INT4)

### 2. Test intégration mémoire – Prompt avec contexte

**Objectif** : Vérifier que le prompt inclut correctement le contexte mémoire.

**Étapes** :
1. Créer contexte mémoire avec traits et souvenirs
2. Appeler `build_prompt(message, context)`
3. Vérifier format du prompt
4. Générer réponse avec ce prompt
5. Vérifier cohérence avec personnalité

**Critères de validation** :
- ✅ Prompt contient traits formatés
- ✅ Prompt contient souvenirs pertinents
- ✅ Prompt contient objectifs de session
- ✅ Réponse cohérente avec personnalité (évaluation manuelle)

### 3. Test quantisation – INT4 vs INT8 vs FP32

**Objectif** : Vérifier que la quantisation fonctionne et réduit la mémoire.

**Étapes** :
1. Charger modèle INT4, mesurer mémoire
2. Charger modèle INT8, mesurer mémoire
3. Charger modèle FP32, mesurer mémoire
4. Comparer qualité des réponses

**Critères de validation** :
- ✅ INT4 : < 200 MB RAM
- ✅ INT8 : < 400 MB RAM
- ✅ FP32 : < 600 MB RAM
- ✅ Qualité INT4 acceptable (dégradation < 10%)

### 4. Test fallback – Erreur locale → API externe

**Objectif** : Vérifier que le fallback vers API externe fonctionne.

**Étapes** :
1. Configurer LocalLLMAdapter avec fallback
2. Simuler erreur (timeout, OOM, etc.)
3. Vérifier que fallback est déclenché
4. Vérifier que réponse API externe est retournée

**Critères de validation** :
- ✅ Erreur détectée correctement
- ✅ Fallback déclenché automatiquement
- ✅ Réponse API externe retournée
- ✅ Logging de l'erreur et du fallback

### 5. Test performance – Latence et mémoire

**Objectif** : Vérifier que les performances sont acceptables.

**Étapes** :
1. Mesurer latence génération (100 requêtes)
2. Mesurer mémoire utilisée
3. Mesurer temps de chargement initial
4. Comparer avec API externe (baseline)

**Critères de validation** :
- ✅ Latence moyenne < 2 secondes (CPU)
- ✅ Latence P95 < 5 secondes
- ✅ Mémoire < 200 MB (quantisé)
- ✅ Temps chargement initial < 30 secondes

### 6. Test qualité – Cohérence personnalité

**Objectif** : Vérifier que les réponses sont cohérentes avec la personnalité.

**Étapes** :
1. Configurer personnalité LIA (traits spécifiques)
2. Générer 10 réponses avec contexte
3. Évaluer manuellement la cohérence
4. Comparer avec API externe (baseline)

**Critères de validation** :
- ✅ Réponses cohérentes avec traits (évaluation manuelle)
- ✅ Ton respecté (calme, curieux, etc.)
- ✅ Style respecté (réfléchi, analytique, etc.)
- ✅ Qualité acceptable (≥ 70% vs API externe)

### 7. Test limites – Tokens et mémoire

**Objectif** : Vérifier la gestion des limites (tokens, mémoire).

**Étapes** :
1. Tester avec prompt très long (> 512 tokens)
2. Tester avec max_tokens très élevé
3. Tester avec mémoire limitée
4. Vérifier gestion des erreurs

**Critères de validation** :
- ✅ Prompt tronqué si > 512 tokens
- ✅ Génération limitée à max_tokens
- ✅ Erreur OOM gérée avec fallback
- ✅ Messages d'erreur clairs

### 8. Test cache – Réutilisation modèle

**Objectif** : Vérifier que le cache du modèle fonctionne.

**Étapes** :
1. Charger modèle (premier appel)
2. Générer plusieurs réponses
3. Vérifier que modèle reste en mémoire
4. Vérifier que latence diminue après premier appel

**Critères de validation** :
- ✅ Modèle chargé une seule fois
- ✅ Latence réduite après premier appel
- ✅ Mémoire stable (pas de fuite)
- ✅ Déchargement manuel fonctionne

### 9. Test GPU – Accélération optionnelle

**Objectif** : Vérifier que GPU est utilisé si disponible.

**Étapes** :
1. Détecter GPU (CUDA)
2. Charger modèle sur GPU
3. Mesurer latence (devrait être < CPU)
4. Vérifier utilisation GPU

**Critères de validation** :
- ✅ GPU détecté automatiquement
- ✅ Modèle chargé sur GPU
- ✅ Latence réduite vs CPU
- ✅ Fallback CPU si GPU indisponible

### 10. Test migration progressive

**Objectif** : Vérifier le processus de migration (parallèle → mixte → local).

**Étapes** :
1. Phase 1 : LocalLLMAdapter testé en parallèle
2. Phase 2 : 50% local, 50% API
3. Phase 3 : 100% local avec fallback
4. Comparer métriques (latence, qualité, coûts)

**Critères de validation** :
- ✅ Migration progressive sans interruption
- ✅ Métriques comparables (qualité, latence)
- ✅ Fallback fonctionne en production
- ✅ Documentation migration complète

## Tests unitaires

### Module LocalLLMAdapter

- Chargement modèle
- Construction prompt
- Génération réponse
- Gestion erreurs
- Fallback
- Cache
- Quantisation

### Module Prompt Builder

- Formatage traits
- Formatage souvenirs
- Formatage objectifs
- Limite tokens
- Troncature prompt

## Tests d'intégration

### Intégration memory_service

- Récupération contexte (`GET /context`)
- Construction prompt avec contexte
- Journalisation interaction (`POST /interaction`)

### Intégration simulation_service

- Utilisation dans simulation multi-agent
- Génération réponses cohérentes
- Gestion erreurs dans simulation

## Critères d'acceptation globaux

- ✅ `LocalLLMAdapter` peut générer des réponses avec GPT-2 Small
- ✅ Le prompt inclut automatiquement les traits et souvenirs de LIA
- ✅ Les réponses sont cohérentes avec la personnalité stockée dans la mémoire
- ✅ Le modèle utilise < 200 MB de RAM (quantisé)
- ✅ Fallback vers API externe si le modèle local échoue
- ✅ Documentation complète disponible
- ✅ Tests passent avec succès (> 80% couverture)

## Outillage

- **pytest** : Tests unitaires et d'intégration
- **pytest-cov** : Couverture de code (objectif : >80%)
- **pytest-asyncio** : Tests asynchrones
- **transformers** : Chargement GPT-2
- **torch** : Backend PyTorch
- **memory_profiler** : Profiling mémoire
- **time** : Mesure latence

## Scripts de test

```bash
# Tests unitaires
pytest tests/unit/test_local_llm_adapter.py -v

# Tests d'intégration
pytest tests/integration/test_local_llm_memory.py -v

# Tests performance
pytest tests/performance/test_local_llm_perf.py -v --benchmark

# Tests complets
pytest tests/ -v --cov=simulation_service.adapters

# Test spécifique
pytest tests/unit/test_local_llm_adapter.py::test_load_model -v
```

## Métriques de validation

| Métrique | Cible | Mesure |
| --- | --- | --- |
| Latence moyenne | < 2s | Temps génération |
| Latence P95 | < 5s | Temps génération |
| Mémoire | < 200 MB | RAM utilisée |
| Qualité | ≥ 70% | vs API externe |
| Taux erreur | < 5% | Erreurs nécessitant fallback |
| Couverture tests | > 80% | Code coverage |



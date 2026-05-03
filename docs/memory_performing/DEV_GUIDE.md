# Guide Développeur - Système de Planification Cognitive

## Architecture

Le système de planification cognitive est composé de plusieurs modules :

### Modules Principaux

1. **`cognitive_models.py`** : Modèles de données
   - `ActionType`, `Action`, `ActionPlan`
   - `ExecutionResult`, `VerificationResult`
   - `Pattern`, `RequestAnalysis`

2. **`cognitive_planner.py`** : Planificateur
   - Analyse les requêtes
   - Propose un **menu d'actions** (par défaut) pour permettre à LIA de choisir itérativement ses actions
   - Utilise les patterns préférés

3. **`action_executor.py`** : Exécuteur
   - Exécute les plans d'actions
   - Interagit avec la mémoire et outils externes

4. **`prompt_builder.py`** : Constructeur de prompts
   - Assemble le prompt final dynamiquement
   - Utilise les résultats d'exécution

5. **`self_verifier.py`** : Auto-vérificateur
   - Vérifie la pertinence des réponses
   - Valide l'utilisation mémoire

6. **`pattern_learner.py`** : Apprenant de patterns
   - Enregistre les exécutions
   - Apprend les patterns efficaces

7. **`cognitive_safeguards.py`** : Garde-fous
   - Protège contre l'explosion de complexité
   - Détecte les boucles

8. **`cognitive_optimizer.py`** : Optimiseur
   - Cache des décisions
   - Parallélisation

9. **`cognitive_metrics.py`** : Métriques
   - Collecte les métriques de performance
   - Statistiques par session et globales

## Extension du Système

## Modes de décision (important)

Le besoin annoncé dans `prompt_memory_performing.md` est : **LIA choisit itérativement quoi consulter** (mémoire, identité, externe) avant de répondre.

Dans l'implémentation, cela correspond à :

- **`cognitive_decision_mode="menu"` (défaut)** : boucle *propose → choisit → exécute → répète → RESPOND*

Exemple :

```python
from core import LLMAdapter, CoreConfig

adapter = LLMAdapter(
    config=CoreConfig(model_path="path/to/model"),
    use_memory=True,
    use_cognitive_planner=True,
    cognitive_decision_mode="menu",
)
```

### Ajouter un Nouveau Type d'Action

1. Ajouter dans `cognitive_models.py` :

```python
class ActionType(str, Enum):
    # ... actions existantes
    NEW_ACTION = "new_action"
```

2. Implémenter dans `action_executor.py` :

```python
async def execute_action(self, action: Action, ...):
    if action.type == ActionType.NEW_ACTION:
        # Implémentation
        return result
```

3. Utiliser dans `cognitive_planner.py` :

```python
if condition:
    actions.append(Action(ActionType.NEW_ACTION, params, priority=priority))
```

### Ajouter une Nouvelle Métrique

1. Ajouter dans `ExecutionMetrics` :

```python
@dataclass
class ExecutionMetrics:
    # ... métriques existantes
    new_metric: float = 0.0
```

2. Enregistrer dans `llm_adapter.py` :

```python
self.metrics.record_execution(
    # ... autres paramètres
    new_metric=value
)
```

### Personnaliser les Garde-fous

```python
from core.cognitive_safeguards import SafeguardConfig, CognitiveSafeguards

custom_config = SafeguardConfig(
    max_decision_depth=5,  # Augmenter la profondeur
    max_reflection_tokens=1000,  # Plus de tokens
    # ... autres paramètres
)

safeguards = CognitiveSafeguards(config=custom_config)
```

## Tests

### Exécuter les Tests

```bash
# Tous les tests
pytest core/tests/

# Tests spécifiques
pytest core/tests/test_cognitive_planner.py
pytest core/tests/test_cognitive_load.py  # Tests de charge
pytest core/tests/test_cognitive_regression.py  # Tests de régression
```

### Ajouter un Nouveau Test

1. Créer dans `core/tests/test_*.py`
2. Utiliser les fixtures existantes
3. Suivre les conventions pytest

Exemple :

```python
@pytest.mark.asyncio
async def test_my_feature(full_system):
    planner = full_system["planner"]
    plan = await planner.plan("test", session_id="test")
    assert plan is not None
```

## Debugging

### Activer les Logs Détaillés

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### Vérifier les Métriques

```python
# Statistiques globales
stats = adapter.metrics.get_global_stats()
print(stats)

# Statistiques par session
session_stats = adapter.metrics.get_session_stats("session_id")
print(session_stats)
```

### Vérifier les Patterns

```python
# Statistiques des patterns
stats = adapter.pattern_learner.get_pattern_statistics()
print(stats)

# Patterns préférés pour un type de requête
patterns = adapter.pattern_learner.get_preferred_patterns("simple")
print(patterns)
```

### Vérifier les Garde-fous

```python
# Statut du budget
status = adapter.safeguards.get_budget_status("session_id")
print(status)
```

## Performance

### Optimisations Recommandées

1. **Activer le cache** : Réduit les recalculs
2. **Parallélisation** : Accélère l'exécution
3. **Limiter la profondeur** : Évite la récursion
4. **Optimiser les prompts** : Réduit la taille

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code à profiler
response = await adapter.generate("test")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

## Contribution

### Guidelines

1. Suivre les conventions de code existantes
2. Ajouter des tests pour toute nouvelle fonctionnalité
3. Documenter les nouvelles APIs
4. Vérifier que tous les tests passent

### Structure des Commits

```
type(scope): description

[body optionnel]

[footer optionnel]
```

Types : `feat`, `fix`, `docs`, `test`, `refactor`

## Références

- Architecture complète : `docs/memory_performing/ARCHITECTURE_ET_PLAN.md`
- Exemples : `docs/memory_performing/EXEMPLES_IMPLEMENTATION.md`
- Guide utilisateur : `docs/memory_performing/USER_GUIDE.md`


# Exemples d'Utilisation - Système de Planification Cognitive

## Exemple 1 : Utilisation Basique

```python
from core import LLMAdapter, CoreConfig
from memory_service import MemoryAdapter

# Initialiser
memory = MemoryAdapter()
config = CoreConfig(
    model_path="path/to/model",
    max_length=512,
    temperature=0.7
)

adapter = LLMAdapter(
    config=config,
    memory_adapter=memory,
    use_cognitive_planner=True
)

# Générer une réponse
response = await adapter.generate(
    message="Qui es-tu ?",
    session_id="user_123"
)

print(response)
```

## Exemple 2 : Streaming

```python
async for chunk in adapter.generate_stream(
    message="Raconte-moi une histoire",
    session_id="user_123"
):
    print(chunk, end="", flush=True)
```

## Exemple 3 : Accès aux Métriques

```python
# Après plusieurs interactions
stats = adapter.metrics.get_session_stats("user_123")

print(f"Exécutions: {stats['execution_count']}")
print(f"Taux de succès: {stats['success_rate']:.2%}")
print(f"Temps moyen: {stats['avg_total_time']:.3f}s")
print(f"Taux de cache: {stats['cache_hit_rate']:.2f}%")
```

## Exemple 4 : Configuration Personnalisée

```python
from core.cognitive_safeguards import SafeguardConfig, CognitiveSafeguards
from core.cognitive_optimizer import CognitiveOptimizer
from core.cognitive_metrics import CognitiveMetrics

# Configuration garde-fous
safeguard_config = SafeguardConfig(
    max_decision_depth=5,
    max_reflection_tokens=1000,
    max_reflection_time=3.0,
    enable_loop_detection=True
)

# Configuration optimisations
optimizer_config = {
    "enable_cache": True,
    "cache_size": 200,
    "cache_ttl_seconds": 7200.0,
    "enable_parallelization": True
}

# Initialiser manuellement
safeguards = CognitiveSafeguards(config=safeguard_config)
optimizer = CognitiveOptimizer(config=optimizer_config)
metrics = CognitiveMetrics()

# Utiliser avec LLMAdapter (via intégration interne)
```

## Exemple 5 : Utilisation Directe du Planificateur

```python
from core import CognitivePlanner, ActionExecutor
from memory_service import MemoryAdapter

memory = MemoryAdapter()

planner = CognitivePlanner(
    memory_adapter=memory,
    config={"max_depth": 3}
)

executor = ActionExecutor(memory_adapter=memory)

# Planifier
plan = await planner.plan("Qui es-tu ?", session_id="test")

print(f"Plan: {len(plan.actions)} actions")
print(f"Confiance: {plan.confidence:.2f}")
print(f"Coût estimé: {plan.estimated_cost:.2f}")

# Exécuter
result = await executor.execute_plan(plan, session_id="test")
print(f"Résultat: {result.success}")
```

## Exemple 6 : Apprentissage de Patterns

```python
from core import PatternLearner

pattern_learner = PatternLearner(
    memory_adapter=memory,
    config={
        "min_success_rate": 0.7,
        "min_usage_count": 5
    }
)

# Après plusieurs exécutions, récupérer les patterns préférés
patterns = pattern_learner.get_preferred_patterns(
    request_type="simple",
    context={}
)

for pattern in patterns:
    print(f"Pattern: {pattern.action_sequence}")
    print(f"Taux de succès: {pattern.success_rate:.2%}")
    print(f"Utilisations: {pattern.usage_count}")
```

## Exemple 7 : Mémoire Sélective

```python
from memory_service.memory_manager import MemoryManager

memory_manager = MemoryManager(
    memory_adapter=memory,
    config={
        "min_importance_score": 0.6,
        "max_memories_per_interaction": 3
    }
)

# Décider quoi mémoriser
interaction = {
    "prompt": "Je préfère le café au thé",
    "response": "D'accord, je retiens ta préférence.",
    "session_id": "user_123"
}

items = await memory_manager.decide_what_to_store(interaction)

for item in items:
    print(f"À mémoriser: {item.content}")
    print(f"Catégorie: {item.category}")
    print(f"Importance: {item.importance_score:.2f}")

# Stocker
memory_ids = await memory_manager.store_memories(items, session_id="user_123")
```

## Exemple 8 : Monitoring et Debugging

```python
# Vérifier le statut des garde-fous
status = adapter.safeguards.get_budget_status("user_123")
print(f"Tokens utilisés: {status['tokens_used']}/{status['tokens_remaining']}")
print(f"Temps utilisé: {status['time_used']:.2f}s/{status['time_remaining']:.2f}s")

# Statistiques du cache
cache_stats = adapter.optimizer.get_optimization_stats()
print(f"Taux de cache: {cache_stats['cache']['hit_rate']:.2f}%")
print(f"Taille cache: {cache_stats['cache']['size']}/{cache_stats['cache']['max_size']}")

# Statistiques des patterns
pattern_stats = adapter.pattern_learner.get_pattern_statistics()
print(f"Patterns totaux: {pattern_stats['total_patterns']}")
print(f"Patterns préférés: {pattern_stats['preferred_patterns']}")
```

## Exemple 9 : Gestion d'Erreurs

```python
try:
    response = await adapter.generate(
        message="Test",
        session_id="user_123"
    )
except Exception as e:
    # Le système devrait gérer les erreurs gracieusement
    print(f"Erreur: {e}")
    
    # Vérifier les métriques pour diagnostiquer
    stats = adapter.metrics.get_session_stats("user_123")
    if stats['success_rate'] < 0.8:
        print("Taux de succès faible, vérifier la configuration")
```

## Exemple 10 : Migration Progressive

```python
import os

# Feature flag pour migration progressive
USE_COGNITIVE_PLANNER = os.getenv("USE_COGNITIVE_PLANNER", "false").lower() == "true"

adapter = LLMAdapter(
    config=config,
    memory_adapter=memory,
    use_cognitive_planner=USE_COGNITIVE_PLANNER
)

# Comparer les performances
if USE_COGNITIVE_PLANNER:
    # Nouveau système
    stats = adapter.metrics.get_global_stats()
    print(f"Nouveau système - Taux succès: {stats['success_rate']:.2%}")
else:
    # Ancien système
    print("Ancien système actif")
```

## Exemple 11 : Test de Charge

```python
import asyncio
import time

async def test_load(adapter, num_requests=100):
    messages = [f"Requête {i}" for i in range(num_requests)]
    
    start = time.time()
    
    tasks = [
        adapter.generate(msg, session_id=f"load_{i % 10}")
        for i, msg in enumerate(messages)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    avg_time = elapsed / num_requests
    
    print(f"{num_requests} requêtes en {elapsed:.2f}s")
    print(f"Temps moyen: {avg_time:.3f}s par requête")
    
    return responses

# Exécuter
responses = await test_load(adapter, num_requests=50)
```

## Exemple 12 : Personnalisation Complète

```python
from core import (
    LLMAdapter, CoreConfig,
    CognitivePlanner, ActionExecutor,
    PatternLearner, SelfVerifier,
    CognitiveSafeguards, SafeguardConfig,
    CognitiveOptimizer, CognitiveMetrics
)

# Configuration complète
memory = MemoryAdapter()

# Garde-fous
safeguards = CognitiveSafeguards(
    config=SafeguardConfig(
        max_decision_depth=4,
        max_reflection_tokens=800,
        max_reflection_time=2.5
    )
)

# Optimisations
optimizer = CognitiveOptimizer(
    config={
        "enable_cache": True,
        "cache_size": 150,
        "enable_parallelization": True
    }
)

# Métriques
metrics = CognitiveMetrics()

# Patterns
pattern_learner = PatternLearner(
    memory_adapter=memory,
    config={"min_success_rate": 0.75}
)

# Planificateur
planner = CognitivePlanner(
    memory_adapter=memory,
    pattern_learner=pattern_learner,
    safeguards=safeguards,
    optimizer=optimizer
)

# Exécuteur
executor = ActionExecutor(
    memory_adapter=memory,
    pattern_learner=pattern_learner
)

# Vérificateur
verifier = SelfVerifier(
    memory_adapter=memory,
    config={"min_overall_score": 0.7}
)

# Utiliser avec LLMAdapter (intégration automatique)
config = CoreConfig(model_path="path/to/model")
adapter = LLMAdapter(
    config=config,
    memory_adapter=memory,
    use_cognitive_planner=True
)

# Les composants sont automatiquement intégrés
```

## Exemple 13 : Analyse de Performance

```python
# Collecter des métriques sur une période
import time

start_time = time.time()
num_requests = 0

# Simuler des requêtes
for i in range(20):
    await adapter.generate(f"Requête {i}", session_id="perf_test")
    num_requests += 1

elapsed = time.time() - start_time

# Analyser
stats = adapter.metrics.get_session_stats("perf_test")
global_stats = adapter.metrics.get_global_stats()

print("=== Analyse de Performance ===")
print(f"Requêtes: {num_requests}")
print(f"Temps total: {elapsed:.2f}s")
print(f"Temps moyen: {elapsed/num_requests:.3f}s")
print(f"Taux de succès: {stats['success_rate']:.2%}")
print(f"Taux de cache: {stats['cache_hit_rate']:.2f}%")
print(f"Confiance moyenne: {stats['avg_confidence']:.2f}")
```

Ces exemples couvrent les cas d'usage principaux du système de planification cognitive.


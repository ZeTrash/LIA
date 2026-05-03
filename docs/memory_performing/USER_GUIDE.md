# Guide Utilisateur - Système de Planification Cognitive

## Introduction

Le système de planification cognitive de LIA permet une génération de réponses plus intelligente et contextuelle. Au lieu d'utiliser un prompt fixe, LIA construit dynamiquement son contexte en prenant des décisions internes sur quelles informations consulter.

## Activation

Le système est activé par défaut si disponible. Pour l'activer explicitement lors de l'initialisation de `LLMAdapter` :

```python
from core import LLMAdapter, CoreConfig

config = CoreConfig(
    model_path="path/to/model",
    # ... autres paramètres
)

adapter = LLMAdapter(
    config=config,
    use_memory=True,
    use_cognitive_planner=True,         # Activer le système cognitif
    cognitive_decision_mode="menu"      # Par défaut : LIA choisit ses actions via un menu
)
```

### Modes de décision

- **`cognitive_decision_mode="menu"` (défaut)** : boucle interne itérative (proposition d'actions → choix par LIA → exécution → répétition → `RESPOND`)

## Fonctionnalités

### 1. Planification Intelligente

LIA analyse chaque requête et décide automatiquement :
- S'il doit consulter sa mémoire
- S'il doit consulter son identité
- S'il doit rechercher des informations externes
- Quelle séquence d'actions est la plus efficace

### 2. Apprentissage de Patterns

LIA apprend des patterns efficaces au fil du temps :
- Les séquences d'actions qui fonctionnent bien sont réutilisées
- Les patterns sont évalués selon leur taux de succès et qualité
- Les patterns préférés sont utilisés automatiquement

### 3. Mémoire Sélective

LIA ne mémorise que les informations importantes :
- Analyse automatique de l'importance des interactions
- Extraction des informations clés (préférences, faits, contexte)
- Catégorisation automatique (préférence, fait, alerte, contexte)

### 4. Auto-Vérification

LIA vérifie ses réponses avant de les envoyer :
- Vérification de la pertinence
- Vérification de l'utilisation mémoire
- Vérification de la cohérence avec l'identité

### 5. Garde-fous

Le système inclut des protections automatiques :
- Limite de profondeur de décision (évite récursion infinie)
- Budget de réflexion (tokens et temps)
- Détection de boucles cognitives
- Validation automatique des plans

## Utilisation

### Génération Simple

```python
response = await adapter.generate(
    message="Qui es-tu ?",
    session_id="user_123"
)
```

### Génération avec Streaming

```python
async for chunk in adapter.generate_stream(
    message="Raconte-moi une histoire",
    session_id="user_123"
):
    print(chunk, end="", flush=True)
```

### Accès aux Métriques

```python
# Récupérer les statistiques d'une session
stats = adapter.metrics.get_session_stats("user_123")
print(f"Taux de succès: {stats['success_rate']:.2%}")
print(f"Temps moyen: {stats['avg_total_time']:.3f}s")

# Récupérer les statistiques globales
global_stats = adapter.metrics.get_global_stats()
print(f"Total exécutions: {global_stats['total_executions']}")
```

### Accès aux Patterns Appris

```python
# Récupérer les statistiques des patterns
stats = adapter.pattern_learner.get_pattern_statistics()
print(f"Patterns préférés: {stats['preferred_patterns']}")
print(f"Taux de succès moyen: {stats['avg_success_rate']:.2%}")
```

## Configuration

### Garde-fous

```python
from core.cognitive_safeguards import SafeguardConfig

safeguard_config = SafeguardConfig(
    max_decision_depth=3,          # Profondeur maximale
    max_reflection_tokens=500,     # Budget tokens
    max_reflection_time=2.0,       # Budget temps (secondes)
    max_memory_access_cost=100.0,  # Coût mémoire max
    max_actions_per_plan=10,       # Actions max par plan
    enable_loop_detection=True,    # Détection boucles
    max_loop_iterations=3          # Itérations max dans boucle
)
```

### Optimisations

```python
optimizer_config = {
    "enable_cache": True,           # Activer cache
    "cache_size": 100,               # Taille cache
    "cache_ttl_seconds": 3600.0,    # Durée de vie cache
    "enable_parallelization": True,  # Parallélisation
    "enable_prompt_optimization": True  # Optimisation prompts
}
```

### Mémoire Sélective

```python
memory_config = {
    "min_importance_score": 0.6,      # Score minimum pour mémoriser
    "max_memories_per_interaction": 3,  # Max souvenirs par interaction
    "enable_auto_cleanup": True         # Nettoyage automatique
}
```

## Dépannage

### Le système ne s'active pas

Vérifiez que :
- `use_cognitive_planner=True` est passé à `LLMAdapter`
- Les dépendances sont installées
- Les logs ne montrent pas d'erreurs d'initialisation

### Performances lentes

- Vérifiez les métriques pour identifier les goulots d'étranglement
- Réduisez `max_decision_depth` si nécessaire
- Activez le cache (`enable_cache=True`)
- Vérifiez que les garde-fous ne sont pas trop restrictifs

### Mémoire non mémorisée

- Vérifiez `min_importance_score` (peut être trop élevé)
- Vérifiez que `MemoryManager` est initialisé
- Consultez les logs pour voir pourquoi les interactions ne sont pas mémorisées

## Support

Pour plus d'informations, consultez :
- Documentation développeur : `docs/memory_performing/DEV_GUIDE.md`
- Architecture : `docs/memory_performing/ARCHITECTURE_ET_PLAN.md`
- Exemples : `docs/memory_performing/EXEMPLES_IMPLEMENTATION.md`


# Guide de Migration - Système de Planification Cognitive

## Vue d'Ensemble

Ce guide vous aide à migrer du système de prompt fixe vers le nouveau système de planification cognitive.

## Avant la Migration

### Vérifications Préalables

1. **Backup** : Sauvegardez votre base de données et configuration
2. **Tests** : Exécutez tous les tests existants pour établir un baseline
3. **Monitoring** : Configurez le monitoring pour comparer avant/après

### Prérequis

- Python 3.8+
- Toutes les dépendances installées
- Base de données fonctionnelle
- Tests passants

## Migration Progressive

### Phase 1 : Activation avec Feature Flag

Le système peut être activé progressivement avec un feature flag :

```python
# Configuration
USE_COGNITIVE_PLANNER = os.getenv("USE_COGNITIVE_PLANNER", "false").lower() == "true"

adapter = LLMAdapter(
    config=config,
    memory_adapter=memory_adapter,
    use_cognitive_planner=USE_COGNITIVE_PLANNER
)
```

**Avantages** :
- Activation/désactivation facile
- Comparaison A/B possible
- Rollback rapide si problème

### Phase 2 : Migration par Session

Migrer progressivement certaines sessions :

```python
def should_use_cognitive_planner(session_id: str) -> bool:
    # Logique de migration progressive
    # Ex: 10% des sessions d'abord, puis 50%, puis 100%
    return hash(session_id) % 100 < migration_percentage

adapter = LLMAdapter(
    config=config,
    memory_adapter=memory_adapter,
    use_cognitive_planner=should_use_cognitive_planner(session_id)
)
```

### Phase 3 : Migration Complète

Une fois validé, activer pour tous :

```python
adapter = LLMAdapter(
    config=config,
    memory_adapter=memory_adapter,
    use_cognitive_planner=True  # Activé pour tous
)
```

## Changements de Comportement

### Prompt Construction

**Avant** :
```python
# Prompt fixe construit dans build_prompt()
prompt = f"{identity}\n{traits}\n{memories}\n{message}"
```

**Après** :
```python
# Prompt dynamique construit par CognitivePlanner
plan = await planner.plan(message, session_id)
execution_result = await executor.execute_plan(plan, session_id)
prompt = prompt_builder.build_dynamic_prompt(message, execution_result)
```

### Mémoire

**Avant** :
- Toutes les interactions sont mémorisées

**Après** :
- Seules les interactions importantes sont mémorisées
- Extraction automatique d'informations clés
- Catégorisation automatique

### Performance

**Avant** :
- Temps constant (prompt fixe)

**Après** :
- Temps variable selon complexité
- Cache pour optimiser les requêtes similaires
- Parallélisation possible

## Configuration Recommandée

### Pour la Migration

```python
# Configuration conservatrice pour débuter
safeguard_config = SafeguardConfig(
    max_decision_depth=2,  # Limite basse au début
    max_reflection_tokens=300,  # Budget réduit
    max_reflection_time=1.5,
    enable_loop_detection=True
)

optimizer_config = {
    "enable_cache": True,  # Activer cache
    "cache_size": 50,  # Taille modérée
    "enable_parallelization": False  # Désactiver au début
}

memory_config = {
    "min_importance_score": 0.7,  # Seuil élevé au début
    "max_memories_per_interaction": 2
}
```

### Après Stabilisation

```python
# Configuration optimisée
safeguard_config = SafeguardConfig(
    max_decision_depth=3,
    max_reflection_tokens=500,
    max_reflection_time=2.0,
    enable_loop_detection=True
)

optimizer_config = {
    "enable_cache": True,
    "cache_size": 100,
    "enable_parallelization": True
}

memory_config = {
    "min_importance_score": 0.6,
    "max_memories_per_interaction": 3
}
```

## Monitoring Post-Migration

### Métriques à Surveiller

1. **Performance** :
   - Temps de réponse moyen
   - Taux de succès
   - Utilisation CPU/mémoire

2. **Qualité** :
   - Scores de vérification
   - Pertinence des réponses
   - Utilisation mémoire

3. **Stabilité** :
   - Erreurs
   - Timeouts
   - Boucles détectées

### Dashboard Exemple

```python
def print_migration_stats(adapter):
    stats = adapter.metrics.get_global_stats()
    
    print("=== Statistiques Migration ===")
    print(f"Exécutions: {stats['total_executions']}")
    print(f"Taux succès: {stats['success_rate']:.2%}")
    print(f"Temps moyen: {stats['avg_total_time']:.3f}s")
    print(f"Taux cache: {stats['cache_hit_rate']:.2f}%")
    
    # Patterns
    pattern_stats = adapter.pattern_learner.get_pattern_statistics()
    print(f"Patterns appris: {pattern_stats['total_patterns']}")
    print(f"Patterns préférés: {pattern_stats['preferred_patterns']}")
```

## Rollback

### Si Problèmes Détectés

1. **Désactiver le feature flag** :
```python
USE_COGNITIVE_PLANNER = False
```

2. **Vérifier les logs** pour identifier le problème

3. **Analyser les métriques** pour comprendre l'impact

4. **Corriger** et réessayer progressivement

### Plan de Rollback

```python
def rollback_if_needed(adapter):
    stats = adapter.metrics.get_global_stats()
    
    # Critères de rollback
    if stats['success_rate'] < 0.8:
        logger.warning("Taux de succès trop bas, rollback recommandé")
        return True
    
    if stats['avg_total_time'] > 5.0:
        logger.warning("Temps de réponse trop élevé, rollback recommandé")
        return True
    
    return False
```

## Checklist de Migration

- [ ] Backup effectué
- [ ] Tests existants passants
- [ ] Feature flag configuré
- [ ] Monitoring en place
- [ ] Migration progressive planifiée
- [ ] Configuration initiale définie
- [ ] Tests de charge effectués
- [ ] Documentation mise à jour
- [ ] Équipe formée
- [ ] Plan de rollback préparé

## Support

En cas de problème lors de la migration :

1. Consultez les logs détaillés
2. Vérifiez les métriques
3. Testez avec une configuration minimale
4. Consultez la documentation développeur
5. Ouvrez une issue avec les détails

## FAQ

**Q: Puis-je utiliser les deux systèmes en parallèle ?**
R: Oui, avec le feature flag, vous pouvez activer le nouveau système progressivement.

**Q: Les anciens prompts fonctionnent-ils toujours ?**
R: Oui, le système garde l'ancien système comme fallback.

**Q: Comment comparer les performances ?**
R: Utilisez les métriques pour comparer avant/après migration.

**Q: Les patterns sont-ils persistants ?**
R: Oui, ils sont stockés dans `data/patterns.json` par défaut.

**Q: Puis-je personnaliser les garde-fous ?**
R: Oui, via `SafeguardConfig` lors de l'initialisation.


# Plan d'implémentation du Menu Optimal

**Date** : 2025-02-20  
**Statut** : 📋 En planification  
**Version** : 1.0

---

## Vue d'ensemble

Ce document décrit le plan d'implémentation du menu optimal intégré avec MemoryRank V2.

## Phases d'implémentation

### Phase 1 : Extension MemoryStore 

**Objectif** : Ajouter les méthodes nécessaires au `MemoryStore` pour supporter le menu optimal.

#### Tâches

1. **Ajouter `get_top_memories_by_rank()`**
   - Fichier : `memory_service/store.py`
   - Tests : `memory_service/tests/test_store_menu.py`
   - Critère de succès : Récupère les souvenirs triés par MemoryRank

2. **Ajouter `get_memory_links()`**
   - Fichier : `memory_service/store.py`
   - Tests : `memory_service/tests/test_store_menu.py`
   - Critère de succès : Récupère les souvenirs liés triés par poids + MemoryRank

3. **Ajouter `get_top_traits_by_rank()`**
   - Fichier : `memory_service/store.py`
   - Tests : `memory_service/tests/test_store_menu.py`
   - Critère de succès : Récupère les traits triés par poids

4. **Ajouter `search_memories_semantic()`**
   - Fichier : `memory_service/store.py`
   - Tests : `memory_service/tests/test_store_menu.py`
   - Critère de succès : Recherche sémantique avec score combiné

#### Livrables

- Méthodes ajoutées à `MemoryStore`
- Tests unitaires passants
- Documentation des méthodes

### Phase 2 : Composants de navigation 

**Objectif** : Créer les composants de navigation dans la mémoire.

#### Tâches

1. **Créer `MemoryRankNavigator`**
   - Fichier : `core/memory_rank_navigator.py`
   - Méthodes :
     - `get_top_memories()`
     - `get_connected_memories()`
     - `get_top_traits()`
     - `get_identity_phrases()`
   - Tests : `core/tests/test_memory_rank_navigator.py`

2. **Créer `SemanticSearcher`**
   - Fichier : `core/semantic_searcher.py`
   - Méthodes :
     - `search()`
     - `_calculate_similarity()`
   - Tests : `core/tests/test_semantic_searcher.py`

3. **Créer `ContextualActionFilter`**
   - Fichier : `core/contextual_action_filter.py`
   - Méthodes :
     - `filter_actions()`
     - `_is_action_relevant()`
   - Tests : `core/tests/test_contextual_action_filter.py`

#### Livrables

- Composants créés et testés
- Documentation des composants
- Intégration avec `MemoryStore`

### Phase 3 : MenuBuilder 

**Objectif** : Créer le `MenuBuilder` qui construit les menus optimaux.

#### Tâches

1. **Créer `MenuBuilder`**
   - Fichier : `core/menu_builder.py`
   - Méthodes :
     - `build_base_menu()`
     - `build_general_menu()`
     - `build_specific_menu()`
   - Tests : `core/tests/test_menu_builder.py`

2. **Créer `EnhancedAction`**
   - Fichier : `core/cognitive_models.py` (ou nouveau fichier)
   - Extension de `Action` avec informations MemoryRank
   - Tests : `core/tests/test_enhanced_action.py`

3. **Intégrer avec `PatternLearner`**
   - Utiliser les patterns pour les recommandations
   - Enrichir avec contexte MemoryRank
   - Tests d'intégration

#### Livrables

- `MenuBuilder` fonctionnel
- Actions enrichies avec MemoryRank
- Tests d'intégration

### Phase 4 : Intégration CognitivePlanner 

**Objectif** : Intégrer le `MenuBuilder` dans le `CognitivePlanner`.

#### Tâches

1. **Modifier `CognitivePlanner`**
   - Fichier : `core/cognitive_planner.py`
   - Ajouter `MenuBuilder` comme dépendance
   - Modifier `build_action_menu()` pour utiliser `MenuBuilder`
   - Garder l'ancien système en fallback

2. **Gestion du contexte**
   - Enrichir `execution_results` avec contexte MemoryRank
   - Gérer les transitions de menu
   - Tests d'intégration

3. **Tests d'intégration**
   - Tests avec différents types de requêtes
   - Tests de navigation dans les menus
   - Tests de performance

#### Livrables

- `CognitivePlanner` intégré avec `MenuBuilder`
- Tests d'intégration passants
- Documentation de l'intégration

### Phase 5 : Optimisations 

**Objectif** : Optimiser les performances et ajouter des fonctionnalités avancées.

#### Tâches

1. **Cache des top éléments**
   - Créer `MenuCache`
   - Fichier : `core/menu_cache.py`
   - TTL configurable
   - Tests : `core/tests/test_menu_cache.py`

2. **Préchargement intelligent**
   - Créer `MenuPreloader`
   - Fichier : `core/menu_preloader.py`
   - Précharger les données probables
   - Tests : `core/tests/test_menu_preloader.py`

3. **Indexation**
   - Index sur `memory_rank_score` dans la base de données
   - Migration de base de données si nécessaire
   - Tests de performance

#### Livrables

- Cache fonctionnel
- Préchargement intelligent
- Performance optimisée (< 100ms pour construction menu)

### Phase 6 : Tests et validation 

**Objectif** : Tests complets et validation du système.

#### Tâches

1. **Tests unitaires**
   - Couverture > 80%
   - Tous les composants testés
   - Edge cases couverts

2. **Tests d'intégration**
   - Scénarios complets (voir `EXEMPLES_MENU_OPTIMAL.md`)
   - Tests de performance
   - Tests de compatibilité avec MemoryRank V1/V2

3. **Tests de régression**
   - Vérifier que l'ancien système fonctionne toujours
   - Tests avec données existantes
   - Validation des patterns existants

#### Livrables

- Suite de tests complète
- Rapport de couverture
- Documentation des tests

### Phase 7 : Documentation et migration 

**Objectif** : Documentation complète et guide de migration.

#### Tâches

1. **Documentation utilisateur**
   - Guide d'utilisation du menu optimal
   - Exemples d'utilisation
   - FAQ

2. **Documentation développeur**
   - Architecture détaillée
   - Guide d'extension
   - API reference

3. **Guide de migration**
   - Migration depuis l'ancien système
   - Configuration
   - Dépannage

#### Livrables

- Documentation complète
- Guide de migration
- Exemples d'utilisation

## Estimation totale

- **Complexité** : Moyenne à élevée
- **Risques** : Intégration avec système existant, performance

## Ordre d'implémentation recommandé

1. Phase 1 (MemoryStore) → Base nécessaire
2. Phase 2 (Composants) → Blocs de construction
3. Phase 3 (MenuBuilder) → Cœur du système
4. Phase 4 (Intégration) → Intégration avec système existant
5. Phase 5 (Optimisations) → Amélioration performance
6. Phase 6 (Tests) → Validation
7. Phase 7 (Documentation) → Finalisation

## Critères de succès

### Fonctionnels

- ✅ Menu de base fonctionne avec MemoryRank
- ✅ Menu général affiche les éléments triés par MemoryRank
- ✅ Recherche sémantique fonctionne
- ✅ Navigation dans le graphe fonctionne
- ✅ Patterns adaptatifs fonctionnent
- ✅ Compatibilité avec MemoryRank V1/V2

### Performance

- ✅ Construction menu < 100ms
- ✅ Recherche sémantique < 200ms
- ✅ Navigation graphe < 50ms
- ✅ Cache efficace (hit rate > 70%)

### Qualité

- ✅ Tests unitaires > 80% couverture
- ✅ Tests d'intégration passants
- ✅ Documentation complète
- ✅ Code maintenable et extensible

## Risques et mitigation

### Risque 1 : Performance

**Risque** : Recherche sémantique trop lente avec beaucoup de souvenirs.

**Mitigation** :
- Cache des résultats
- Indexation sur `memory_rank_score`
- Limite sur le nombre de souvenirs comparés
- Optimisation progressive

### Risque 2 : Compatibilité

**Risque** : Incompatibilité avec l'ancien système.

**Mitigation** :
- Garder l'ancien système en fallback
- Migration progressive
- Tests de régression

### Risque 3 : Complexité

**Risque** : Système trop complexe à maintenir.

**Mitigation** :
- Architecture modulaire
- Documentation complète
- Tests exhaustifs
- Code review

## Prochaines étapes

1. **Révision du plan** : Valider avec l'équipe
2. **Démarrage Phase 1** : Commencer par l'extension MemoryStore
3. **Itérations** : Implémenter phase par phase avec validation

## Références

- **Concept** : `CONCEPT_MENU_OPTIMAL.md`
- **Architecture** : `ARCHITECTURE_MENU_OPTIMAL.md`
- **Intégration** : `INTEGRATION_MEMORY_MENU.md`
- **Exemples** : `EXEMPLES_MENU_OPTIMAL.md`


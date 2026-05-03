# Intégration Menu Optimal avec MemoryRank V2

**Date** : 2025-02-20  
**Statut** : 📋 En conception  
**Version** : 1.0

---

## Vue d'ensemble

Ce document décrit comment intégrer le menu optimal avec le système MemoryRank V2 existant.

## Points d'intégration

### 1. MemoryStore existant

Le `MemoryStore` actuel doit être étendu pour supporter les nouvelles fonctionnalités du menu.

#### Méthodes à ajouter

```python
# Dans memory_service/store.py

class MemoryStore:
    # ... méthodes existantes ...
    
    def get_top_memories_by_rank(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        min_rank: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Récupère les souvenirs triés par MemoryRank.
        
        Utilise memory_rank_score pour trier.
        """
        session = self.db.get_session()
        try:
            query = session.query(SouvenirModel).filter(
                SouvenirModel.memory_rank_score >= min_rank
            )
            
            if category:
                query = query.filter(SouvenirModel.category == category)
            
            memories = query.order_by(
                SouvenirModel.memory_rank_score.desc()
            ).limit(limit).all()
            
            return [self._memory_to_dict(m) for m in memories]
        finally:
            session.close()
    
    def get_memory_links(
        self,
        memory_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Récupère les souvenirs liés via MemoryRank.
        
        Retourne les souvenirs connectés, triés par poids de lien + MemoryRank.
        """
        session = self.db.get_session()
        try:
            # Récupérer les liens sortants
            links = session.query(MemoryLinkModel).filter(
                MemoryLinkModel.source_memory_id == memory_id
            ).order_by(
                MemoryLinkModel.weight.desc()
            ).limit(limit).all()
            
            # Récupérer les souvenirs cibles
            target_ids = [l.target_memory_id for l in links]
            memories = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id.in_(target_ids)
            ).all()
            
            # Créer dict avec poids de lien
            memory_dict = {m.memory_id: self._memory_to_dict(m) for m in memories}
            result = []
            for link in links:
                if link.target_memory_id in memory_dict:
                    mem = memory_dict[link.target_memory_id]
                    mem['link_weight'] = link.weight
                    mem['link_type'] = link.link_type
                    result.append(mem)
            
            # Trier par poids de lien + MemoryRank
            result.sort(
                key=lambda x: (
                    x.get('link_weight', 0.0),
                    x.get('memory_rank_score', 0.0)
                ),
                reverse=True
            )
            
            return result[:limit]
        finally:
            session.close()
    
    def get_top_traits_by_rank(
        self,
        limit: int = 10,
        trait_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les traits triés par MemoryRank.
        
        Pour les traits, on utilise le poids (weight) comme proxy de MemoryRank.
        """
        session = self.db.get_session()
        try:
            query = session.query(TraitModel)
            
            if trait_type:
                query = query.filter(TraitModel.trait_type == trait_type)
            
            traits = query.order_by(
                TraitModel.weight.desc()
            ).limit(limit).all()
            
            return [self._trait_to_dict(t) for t in traits]
        finally:
            session.close()
    
    def search_memories_semantic(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        alpha: float = 0.6,  # Poids similarité
        beta: float = 0.4     # Poids MemoryRank
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique dans les souvenirs.
        
        Score final = α·similarité + β·memory_rank
        
        Utilise PhraseSegmenter pour segmenter la requête,
        puis compare avec les souvenirs existants.
        """
        from memory_service.phrase_segmenter import PhraseSegmenter
        from memory_service.semantic_filter import SemanticFilter
        
        # Segmenter la requête
        segmenter = PhraseSegmenter()
        query_phrases = segmenter.segment(query)
        
        if not query_phrases:
            return []
        
        # Récupérer tous les souvenirs (ou filtrés par catégorie)
        session = self.db.get_session()
        try:
            query_db = session.query(SouvenirModel)
            if category:
                query_db = query_db.filter(SouvenirModel.category == category)
            memories = query_db.all()
            
            # Calculer scores pour chaque souvenir
            scored_memories = []
            semantic_filter = SemanticFilter(self)
            
            for memory in memories:
                # Similarité avec la requête
                similarity = semantic_filter._calculate_novelty(
                    query_phrases[0],  # Utiliser première phrase de la requête
                    memory.content
                )
                
                # MemoryRank
                memory_rank = float(memory.memory_rank_score or 0.0)
                
                # Score combiné
                combined_score = alpha * similarity + beta * memory_rank
                
                scored_memories.append({
                    'memory': memory,
                    'score': combined_score,
                    'similarity': similarity,
                    'memory_rank': memory_rank
                })
            
            # Trier par score
            scored_memories.sort(key=lambda x: x['score'], reverse=True)
            
            # Retourner les top résultats
            result = []
            for item in scored_memories[:limit]:
                mem_dict = self._memory_to_dict(item['memory'])
                mem_dict['search_score'] = item['score']
                mem_dict['search_similarity'] = item['similarity']
                result.append(mem_dict)
            
            return result
        finally:
            session.close()
```

### 2. CognitivePlanner existant

Le `CognitivePlanner` doit être étendu pour utiliser le nouveau `MenuBuilder`.

#### Modifications

```python
# Dans core/cognitive_planner.py

class CognitivePlanner:
    def __init__(
        self,
        memory_adapter: MemoryAdapter,
        pattern_learner: PatternLearner,
        config: PlannerConfig,
        menu_builder: Optional[MenuBuilder] = None  # Nouveau
    ):
        # ... existant ...
        self.menu_builder = menu_builder or MenuBuilder(
            memory_store=memory_adapter.store,
            pattern_learner=pattern_learner
        )
    
    def build_action_menu(
        self,
        user_message: str,
        execution_results: Optional[Dict[str, Any]] = None,
        session_id: str = "default",
    ) -> List[Action]:
        """Construit le menu avec le MenuBuilder."""
        state = str(execution_results.get("_menu_state") or "base")
        
        if state == "base":
            return self.menu_builder.build_base_menu(
                user_message,
                execution_results or {},
                session_id
            )
        elif state == "general":
            return self.menu_builder.build_general_menu(
                user_message,
                execution_results or {},
                session_id
            )
        elif state.startswith("specific:"):
            menu_type = state.split(":", 1)[1]
            return self.menu_builder.build_specific_menu(
                menu_type,
                user_message,
                execution_results or {},
                session_id
            )
        else:
            # Fallback sur ancien système
            return self._build_action_menu_legacy(
                user_message,
                execution_results,
                session_id
            )
```

### 3. LLMAdapter existant

Le `LLMAdapter` doit utiliser le nouveau système de menu.

#### Aucune modification nécessaire

Le `LLMAdapter` utilise déjà `CognitivePlanner.build_action_menu()`, donc les modifications dans `CognitivePlanner` suffisent.

### 4. PhraseMemoryProcessor

Le `PhraseMemoryProcessor` peut être utilisé pour améliorer la recherche sémantique.

#### Utilisation

```python
# Dans SemanticSearcher

from memory_service.phrase_memory_processor import PhraseMemoryProcessor

class SemanticSearcher:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.phrase_processor = PhraseMemoryProcessor(
            memory_store=memory_store
        )
    
    def search(self, query: str, limit: int = 10):
        """
        Utilise PhraseMemoryProcessor pour segmenter et comparer.
        """
        # Segmenter la requête
        query_segments = self.phrase_processor.segmenter.segment(query)
        
        # Récupérer les phrases mémorisées (via MemoryStore)
        # Comparer avec query_segments
        # ...
```

## Migration progressive

### Phase 1 : Extension MemoryStore

1. Ajouter les nouvelles méthodes à `MemoryStore`
2. Tests unitaires pour chaque méthode
3. Validation avec données existantes

### Phase 2 : Création MenuBuilder

1. Créer `MenuBuilder` dans `core/menu_builder.py`
2. Créer `MemoryRankNavigator` dans `core/memory_rank_navigator.py`
3. Créer `SemanticSearcher` dans `core/semantic_searcher.py`
4. Tests unitaires

### Phase 3 : Intégration CognitivePlanner

1. Modifier `CognitivePlanner` pour utiliser `MenuBuilder`
2. Garder l'ancien système en fallback
3. Tests d'intégration

### Phase 4 : Activation progressive

1. Activer le nouveau menu pour certaines requêtes
2. Comparer avec l'ancien système
3. Ajuster selon les résultats

### Phase 5 : Migration complète

1. Désactiver l'ancien système
2. Nettoyer le code legacy
3. Documentation finale

## Compatibilité

### Avec MemoryRank V1

Le menu optimal fonctionne avec MemoryRank V1 et V2 :
- V1 : Utilise `memory_rank_score` calculé sur les souvenirs complets
- V2 : Utilise `memory_rank_score` calculé sur les phrases

### Avec Patterns existants

Les patterns existants continuent de fonctionner :
- Le `PatternLearner` est utilisé par `MenuBuilder`
- Les patterns sont enrichis avec le contexte MemoryRank

### Avec l'ancien menu

L'ancien système de menu reste disponible en fallback :
- Si `MenuBuilder` n'est pas disponible, utiliser l'ancien système
- Migration progressive possible

## Tests d'intégration

### Test 1 : Menu de base avec MemoryRank

```python
async def test_base_menu_with_memory_rank():
    """Test menu de base avec MemoryRank."""
    store = MemoryStore(use_memory_rank=True)
    planner = CognitivePlanner(memory_adapter, pattern_learner, config)
    
    # Créer quelques souvenirs avec MemoryRank
    # ...
    
    menu = await planner.build_action_menu(
        "Qui es-tu ?",
        execution_results={"_menu_state": "base"}
    )
    
    # Vérifier que les actions sont enrichies avec MemoryRank
    assert any(a.memory_rank_hint is not None for a in menu)
```

### Test 2 : Recherche sémantique

```python
async def test_semantic_search():
    """Test recherche sémantique."""
    store = MemoryStore(use_memory_rank=True)
    searcher = SemanticSearcher(store)
    
    # Créer souvenirs
    # ...
    
    results = searcher.search("Python programming", limit=5)
    
    # Vérifier que les résultats sont triés par score combiné
    assert len(results) <= 5
    assert results[0]['search_score'] >= results[-1]['search_score']
```

### Test 3 : Navigation dans le graphe

```python
async def test_graph_navigation():
    """Test navigation dans le graphe MemoryRank."""
    store = MemoryStore(use_memory_rank=True)
    navigator = MemoryRankNavigator(store)
    
    # Créer souvenirs avec liens
    # ...
    
    connected = navigator.get_connected_memories(memory_id="mem_1", limit=5)
    
    # Vérifier que les résultats sont triés par poids de lien + MemoryRank
    assert len(connected) <= 5
```

## Performance

### Optimisations

1. **Cache** : Cache des top éléments (TTL 60s)
2. **Préchargement** : Précharger les données probables
3. **Lazy loading** : Charger les détails seulement si nécessaire
4. **Indexation** : Index sur `memory_rank_score` pour tri rapide

### Métriques

- Temps de construction du menu : < 100ms
- Temps de recherche sémantique : < 200ms
- Temps de navigation graphe : < 50ms

## Prochaines étapes

1. **Implémentation** : Voir `PLAN_IMPLEMENTATION_MENU.md`
2. **Exemples** : Voir `EXEMPLES_MENU_OPTIMAL.md`



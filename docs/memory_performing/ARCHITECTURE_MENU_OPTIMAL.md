# Architecture du Menu Optimal

**Date** : 2025-02-20  
**Statut** : 📋 En conception  
**Version** : 1.0

---

## Vue d'ensemble

Ce document décrit l'architecture technique du menu optimal, intégré avec MemoryRank V2.

## Composants principaux

### 1. MenuBuilder

**Responsabilité** : Construire le menu adapté au contexte.

```python
class MenuBuilder:
    """Construit les menus adaptés au contexte et à la mémoire."""
    
    def __init__(self, memory_store: MemoryStore, pattern_learner: PatternLearner):
        """
        Initialise le MenuBuilder.
        
        Args:
            memory_store: Store pour accéder à la mémoire MemoryRank
            pattern_learner: PatternLearner pour obtenir les recommandations de patterns
                             (utilise Gemini/Groq pour l'apprentissage)
        """
        self.memory_store = memory_store
        self.pattern_learner = pattern_learner  # Utilise Gemini/Groq pour l'apprentissage
    
    def build_base_menu(
        self,
        user_request: str,
        execution_results: Dict[str, Any],
        session_id: str
    ) -> Tuple[List[Action], Optional[Dict[str, Any]]]:
        """
        Construit le menu de base avec actions adaptées.
        
        Utilise les patterns (via PatternLearner) pour suggérer des actions.
        Les patterns sont filtrés par theme_pattern si disponible.
        
        Returns:
            Tuple de (liste d'actions, recommandation de pattern)
        """
        # Récupérer le thème classifié (par Gemini/Groq)
        theme_pattern = execution_results.get("_theme_pattern")
        
        # Obtenir recommandation de pattern
        pattern_rec = self.pattern_learner.get_pattern_recommendation(
            menu_context="base",
            prev_step=execution_results.get("_last_step", "initial"),
            theme_pattern=theme_pattern
        )
        
        # Construire le menu avec actions enrichies MemoryRank
        menu = self._build_menu_actions(user_request, execution_results)
        
        return menu, pattern_rec
    
    def build_general_menu(
        self,
        user_request: str,
        execution_results: Dict[str, Any],
        session_id: str
    ) -> List[Action]:
        """Construit le menu général (connaissance de soi)."""
        pass
    
    def build_specific_menu(
        self,
        menu_type: str,  # "memories", "identity", "traits", "capabilities"
        user_request: str,
        execution_results: Dict[str, Any],
        session_id: str
    ) -> List[Action]:
        """Construit un menu spécifique selon le type."""
        pass
```

### 2. MemoryRankNavigator

**Responsabilité** : Navigation dans la mémoire basée sur MemoryRank.

```python
class MemoryRankNavigator:
    """Navigation intelligente dans la mémoire MemoryRank."""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
    
    def get_top_memories(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        min_rank: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Récupère les souvenirs les plus importants (triés par MemoryRank)."""
        pass
    
    def search_semantic(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Recherche sémantique dans la mémoire."""
        pass
    
    def get_connected_memories(
        self,
        memory_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Récupère les souvenirs liés (via MemoryRank links)."""
        pass
    
    def get_top_traits(
        self,
        limit: int = 10,
        trait_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupère les traits les plus importants."""
        pass
    
    def get_identity_phrases(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Récupère les phrases d'identité les plus importantes."""
        pass
```

### 3. SemanticSearcher

**Responsabilité** : Recherche sémantique dans la mémoire.

```python
class SemanticSearcher:
    """Recherche sémantique dans les phrases mémorisées."""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        # Optionnel : modèle d'embedding pour meilleure similarité
    
    def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique.
        
        Processus :
        1. Segmenter la requête en phrases
        2. Comparer avec les phrases mémorisées
        3. Calculer score = α·similarité + β·memory_rank
        4. Trier et retourner
        """
        pass
    
    def _calculate_similarity(
        self,
        query_phrase: str,
        memory_phrase: str
    ) -> float:
        """Calcule la similarité entre deux phrases."""
        # Utilise Jaccard ou embeddings selon disponibilité
        pass
```

### 4. ContextualActionFilter

**Responsabilité** : Filtrer les actions selon le contexte.

```python
class ContextualActionFilter:
    """Filtre les actions selon le contexte et l'historique."""
    
    def filter_actions(
        self,
        actions: List[Action],
        execution_results: Dict[str, Any],
        user_request: str
    ) -> List[Action]:
        """
        Filtre les actions :
        - Évite les actions déjà effectuées (sauf si pertinentes)
        - Priorise les actions pertinentes au contexte
        - Utilise les patterns pour suggérer des actions
        """
        pass
    
    def _is_action_relevant(
        self,
        action: Action,
        user_request: str,
        execution_results: Dict[str, Any]
    ) -> bool:
        """Détermine si une action est pertinente au contexte."""
        pass
```

## Structure des actions

### Action enrichie

```python
@dataclass
class EnhancedAction(Action):
    """Action enrichie avec informations MemoryRank."""
    
    # Hérite de Action (type, parameters, priority, required)
    
    # Informations MemoryRank
    memory_rank_hint: Optional[float] = None  # Score MemoryRank si applicable
    semantic_relevance: Optional[float] = None  # Pertinence sémantique à la requête
    connection_count: Optional[int] = None  # Nombre de connexions dans le graphe
    
    # Métadonnées
    estimated_results_count: Optional[int] = None  # Nombre estimé de résultats
    category: Optional[str] = None  # Catégorie de l'action
```

## Flux de construction du menu

### 1. Menu de base

```
User Request
    │
    ├─→ [ContextualActionFilter] → Filtrer actions pertinentes
    │
    ├─→ [PatternLearner] → Obtenir recommandations de patterns
    │
    ├─→ [MenuBuilder.build_base_menu] → Construire menu
    │       │
    │       ├─→ Action B1: Analyser requête
    │       ├─→ Action B2: Rechercher dans mémoire (si pertinente)
    │       ├─→ Action B3: Consulter connaissance de soi
    │       ├─→ Action B4: Consulter patterns (optionnel)
    │       └─→ Action B5: Répondre
    │
    └─→ [Enrichir avec MemoryRank] → Ajouter hints de pertinence
```

### 2. Menu général

```
Menu Général Demandé
    │
    ├─→ [MemoryRankNavigator] → Récupérer top éléments
    │       │
    │       ├─→ Top traits (triés par MemoryRank)
    │       ├─→ Top identité (triés par MemoryRank)
    │       └─→ Top capacités (triés par MemoryRank)
    │
    ├─→ [MenuBuilder.build_general_menu] → Construire menu
    │       │
    │       ├─→ Action G1: Identité (avec hint: N éléments disponibles)
    │       ├─→ Action G2: Traits (avec hint: top 3 = ...)
    │       ├─→ Action G3: Capacités
    │       ├─→ Action G4: Souvenirs (menu spécifique)
    │       ├─→ Action G5: Recherche sémantique
    │       ├─→ Action G6: Répondre
    │       └─→ Action G7: Revenir
    │
    └─→ [Enrichir avec MemoryRank] → Ajouter scores et connexions
```

### 3. Menu spécifique - Souvenirs

```
Menu Souvenirs Demandé
    │
    ├─→ [MemoryRankNavigator.get_top_memories] → Top souvenirs
    │
    ├─→ [SemanticSearcher] → Préparer recherche (si requête fournie)
    │
    ├─→ [MenuBuilder.build_specific_menu] → Construire menu
    │       │
    │       ├─→ Action S1: Top souvenirs (avec preview: 3 premiers)
    │       ├─→ Action S2: Recherche sémantique
    │       ├─→ Action S3: Explorer connexions (si souvenir sélectionné)
    │       ├─→ Action S4: Souvenirs récents
    │       ├─→ Action S5: Par catégorie
    │       ├─→ Action S6: Répondre
    │       └─→ Action S7: Revenir
    │
    └─→ [Enrichir avec MemoryRank] → Ajouter scores et liens
```

## Intégration avec MemoryStore

### Méthodes à ajouter/extendre

```python
class MemoryStore:
    # Méthodes existantes...
    
    def get_top_memories_by_rank(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        min_rank: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Récupère les souvenirs triés par MemoryRank."""
        pass
    
    def get_memory_links(
        self,
        memory_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Récupère les souvenirs liés via MemoryRank."""
        pass
    
    def get_top_traits_by_rank(
        self,
        limit: int = 10,
        trait_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupère les traits triés par MemoryRank."""
        pass
    
    def search_memories_semantic(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Recherche sémantique dans les souvenirs."""
        pass
```

## Gestion du contexte

### ExecutionResults enrichi

```python
execution_results = {
    # Existant
    "_menu_state": "base" | "general" | "specific",
    "_chosen_actions": [...],
    
    # Nouveau : Contexte MemoryRank
    "_memory_context": {
        "top_memories_preview": [...],  # Preview des top souvenirs
        "top_traits_preview": [...],     # Preview des top traits
        "search_results_preview": [...], # Preview des résultats de recherche
        "current_memory_id": "...",      # Souvenir actuellement consulté
        "navigation_path": [...],        # Chemin de navigation dans le graphe
    },
    
    # Nouveau : Métriques
    "_menu_metrics": {
        "actions_available": 5,
        "memory_rank_avg": 0.15,
        "semantic_relevance_avg": 0.7,
    }
}
```

## Optimisations

### 1. Cache des top éléments

```python
class MenuCache:
    """Cache pour éviter de recalculer les top éléments."""
    
    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.ttl = ttl
    
    def get_top_memories(self, limit: int, category: Optional[str] = None):
        """Récupère depuis cache ou recalcule."""
        key = f"top_memories_{limit}_{category}"
        if key in self.cache and not self._is_expired(key):
            return self.cache[key]
        
        result = self._compute_top_memories(limit, category)
        self.cache[key] = result
        return result
```

### 2. Préchargement intelligent

```python
class MenuPreloader:
    """Précharge les données probables pour accélérer le menu."""
    
    def preload_for_base_menu(self, user_request: str):
        """Précharge les données probables pour le menu de base."""
        # Précharge top souvenirs, top traits, etc.
        pass
```

## Patterns adaptatifs

### Intégration avec PatternLearner (Gemini/Groq)

Le `PatternLearner` existant utilise Gemini/Groq pour :
1. **Classification du thème** : Avant la planification, classe la requête dans un thème
2. **Apprentissage** : Après chaque interaction, apprend les patterns optimaux

Le `MenuBuilder` utilise ces patterns pour suggérer des actions :

```python
class MenuBuilder:
    def build_base_menu(self, user_request, execution_results, session_id):
        # Récupérer le thème classifié (par Gemini/Groq)
        theme_pattern = execution_results.get("_theme_pattern")
        
        # Obtenir recommandation depuis PatternLearner
        pattern_rec = self.pattern_learner.get_pattern_recommendation(
            menu_context="base",
            prev_step="initial",
            theme_pattern=theme_pattern  # Filtre par thème
        )
        
        # pattern_rec contient :
        # - recommended_step: code de l'action recommandée (ex: "B3")
        # - confidence: confiance dans la recommandation
        # - theme_pattern: thème utilisé
        
        return menu, pattern_rec
```

### PatternLearner enrichi avec MemoryRank

```python
class EnhancedPatternLearner(PatternLearner):
    """PatternLearner enrichi avec contexte MemoryRank."""
    
    def get_recommendation_with_context(
        self,
        menu_context: str,
        prev_step: str,
        user_request: str,
        memory_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Recommandation enrichie avec contexte MemoryRank.
        
        Prend en compte :
        - Patterns appris (via Gemini/Groq)
        - Structure MemoryRank (concepts centraux)
        - Connexions fréquentes
        - Pertinence sémantique
        
        Note: L'apprentissage des patterns se fait toujours via Gemini/Groq
        dans _learn_menu_patterns_with_agent().
        """
        # 1. Récupérer pattern de base
        base_pattern = self.get_pattern_recommendation(
            menu_context=menu_context,
            prev_step=prev_step,
            theme_pattern=memory_context.get("theme_pattern")
        )
        
        # 2. Enrichir avec MemoryRank
        if base_pattern:
            # Calculer pertinence MemoryRank pour l'action recommandée
            memory_rank_score = self._calculate_memory_rank_relevance(
                base_pattern["recommended_step"],
                user_request,
                memory_context
            )
            
            base_pattern["memory_rank_relevance"] = memory_rank_score
            base_pattern["combined_score"] = (
                0.6 * base_pattern["confidence"] +
                0.4 * memory_rank_score
            )
        
        return base_pattern
```

## Tests

### Tests unitaires

```python
def test_menu_builder_base_menu():
    """Test construction menu de base."""
    pass

def test_memory_rank_navigator_top_memories():
    """Test récupération top souvenirs."""
    pass

def test_semantic_searcher():
    """Test recherche sémantique."""
    pass

def test_contextual_action_filter():
    """Test filtrage contextuel."""
    pass
```

### Tests d'intégration

```python
def test_menu_flow_with_memory_rank():
    """Test flux complet menu avec MemoryRank."""
    pass
```

## Prochaines étapes

1. **Implémentation** : Voir `PLAN_IMPLEMENTATION_MENU.md`
2. **Exemples** : Voir `EXEMPLES_MENU_OPTIMAL.md`
3. **Intégration** : Voir `INTEGRATION_MEMORY_MENU.md`


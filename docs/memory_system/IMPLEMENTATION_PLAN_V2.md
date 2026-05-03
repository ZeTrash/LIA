# Plan d'implémentation - MemoryRank V2

## Objectif

Implémenter le système de segmentation et filtrage sémantique pour MemoryRank V2, permettant de mémoriser des unités sémantiques (phrases) plutôt que des prompts bruts.

## Phases d'implémentation

### Phase 1 : Segmentation en phrases

**Fichier :** `memory_service/phrase_segmenter.py`

**Fonctionnalités :**
- Détection des limites de phrases (ponctuation, structure)
- Nettoyage et normalisation
- Filtrage des phrases trop courtes (< 10 caractères)
- Filtrage des phrases non informatives (ex: "ok", "merci")

**Dépendances :**
- Bibliothèque de traitement de texte (NLTK ou spaCy pour français)
- Expressions régulières pour nettoyage

**Tests :**
- Segmentation correcte de prompts complexes
- Gestion des cas limites (pas de ponctuation, phrases multiples)
- Performance sur différents types de textes

### Phase 2 : Calcul de nouveauté

**Fichier :** `memory_service/semantic_filter.py`

**Fonctionnalités :**
- Comparaison d'une phrase avec les souvenirs existants
- Calcul de similarité sémantique (embeddings ou TF-IDF)
- Score de nouveauté (1.0 = complètement nouveau, 0.0 = redondant)

**Dépendances :**
- Modèle d'embeddings (sentence-transformers ou OpenAI)
- Base de données pour récupérer les souvenirs existants

**Algorithme :**
```python
def calculate_novelty(phrase: str, existing_memories: List[str]) -> float:
    phrase_embedding = get_embedding(phrase)
    max_similarity = 0.0
    
    for memory in existing_memories:
        memory_embedding = get_embedding(memory)
        similarity = cosine_similarity(phrase_embedding, memory_embedding)
        max_similarity = max(max_similarity, similarity)
    
    # Nouveauté = 1 - similarité maximale
    return 1.0 - max_similarity
```

### Phase 3 : Calcul de lien RL

**Fichier :** `memory_service/rl_scorer.py`

**Fonctionnalités :**
- Historique des récompenses associées à des phrases similaires
- Fréquence d'utilisation dans des contextes réussis
- Score RL basé sur l'utilité passée

**Intégration :**
- Utiliser `RLMemoryRank` existant
- Étendre pour supporter les phrases au lieu des souvenirs complets

**Algorithme :**
```python
def calculate_rl_score(phrase: str, rl_history: List[Dict]) -> float:
    # Chercher des phrases similaires dans l'historique RL
    similar_phrases = find_similar_phrases(phrase, rl_history)
    
    # Calculer la moyenne des récompenses
    if not similar_phrases:
        return 0.5  # Score neutre si pas d'historique
    
    avg_reward = sum(p['reward'] for p in similar_phrases) / len(similar_phrases)
    return avg_reward
```

### Phase 4 : Calcul de centralité MemoryRank

**Fichier :** `memory_service/phrase_memory_rank.py`

**Fonctionnalités :**
- Calcul du score MemoryRank pour chaque phrase
- Utilisation du moteur MemoryRank existant
- Mise à jour incrémentale lors de l'ajout de nouvelles phrases

**Intégration :**
- Réutiliser `MemoryRankEngine`
- Adapter pour travailler avec des phrases au lieu de souvenirs complets

### Phase 5 : Filtrage et décision

**Fichier :** `memory_service/semantic_filter.py` (extension)

**Fonctionnalités :**
- Combinaison des trois scores (nouveauté, RL, centralité)
- Application du seuil θ
- Décision de stockage

**Algorithme :**
```python
def should_store_phrase(phrase: str, config: Dict) -> Tuple[bool, float]:
    novelty = calculate_novelty(phrase, existing_memories)
    rl_score = calculate_rl_score(phrase, rl_history)
    centrality = get_memory_rank_score(phrase)
    
    importance = (
        config['alpha'] * novelty +
        config['beta'] * rl_score +
        config['gamma'] * centrality
    )
    
    should_store = importance > config['threshold']
    return should_store, importance
```

### Phase 6 : Création automatique de liens

**Fichier :** `memory_service/phrase_linker.py`

**Fonctionnalités :**
- Détection de co-occurrences (phrases dans la même interaction)
- Détection de dépendances causales (patterns linguistiques)
- Calcul de similarité embedding pour créer des liens

**Types de liens :**
1. **Co-occurrence** : Automatique lors du traitement d'une interaction
2. **Causal** : Détection via patterns ("parce que", "donc", etc.)
3. **Similarité** : Si similarité embedding > seuil (0.7)

**Intégration :**
- Utiliser `MemoryRankEngine.add_link()` existant
- Créer les liens automatiquement lors du stockage

### Phase 7 : Processeur principal

**Fichier :** `memory_service/phrase_memory_processor.py`

**Fonctionnalités :**
- Orchestration de tout le pipeline
- Interface simple pour traiter une interaction
- Gestion des erreurs et logging

**Interface :**
```python
class PhraseMemoryProcessor:
    async def process_interaction(
        self,
        interaction: Dict[str, Any]
    ) -> List[str]:
        """
        Traite une interaction complète :
        1. Segmentation en phrases
        2. Filtrage sémantique
        3. Stockage des phrases importantes
        4. Création des liens MemoryRank
        
        Returns:
            Liste des IDs des phrases stockées
        """
```

### Phase 8 : Intégration avec le système existant

**Modifications :**
- `MemoryAdapter` : Ajouter méthode pour utiliser le processeur de phrases
- `MemoryStore` : Support pour les phrases comme souvenirs
- `LLMAdapter` : Option pour activer le traitement par phrases

**Configuration :**
```python
# Activer V2 dans MemoryAdapter
memory_adapter = MemoryAdapter(use_phrase_processing=True)

# Ou dans LLMAdapter
llm_adapter = LLMAdapter(use_phrase_memory=True)
```

## Structure des fichiers

```
memory_service/
├── phrase_segmenter.py          # Phase 1
├── semantic_filter.py            # Phase 2, 5
├── rl_scorer.py                 # Phase 3
├── phrase_memory_rank.py         # Phase 4
├── phrase_linker.py              # Phase 6
├── phrase_memory_processor.py    # Phase 7
└── tests/
    ├── test_phrase_segmenter.py
    ├── test_semantic_filter.py
    └── test_phrase_memory_processor.py
```

## Dépendances à ajouter

```txt
# Pour segmentation
nltk>=3.8
# ou
spacy>=3.4

# Pour embeddings (optionnel, peut utiliser API)
sentence-transformers>=2.2.0
# ou
openai>=1.0.0  # Pour embeddings OpenAI

# Pour similarité
scikit-learn>=1.3.0  # Pour cosine_similarity
```

## Tests à créer

1. **Test segmentation** : Vérifier la segmentation correcte
2. **Test nouveauté** : Vérifier le calcul de nouveauté
3. **Test filtrage** : Vérifier que seules les phrases importantes sont stockées
4. **Test liens** : Vérifier la création automatique de liens
5. **Test intégration** : Test end-to-end avec une interaction complète

## Migration depuis V1

**Stratégie :**
- V2 peut coexister avec V1
- Option pour activer/désactiver V2
- Migration progressive possible en reprocessant les interactions existantes

**Script de migration :**
```python
# Reprocesser les interactions existantes avec V2
migrate_to_v2(existing_interactions)
```

## Métriques de succès

- **Réduction mémoire** : 50-70% de réduction vs V1
- **Qualité** : Score de pertinence > 0.8
- **Performance** : Traitement < 1s par interaction
- **Précision** : 90%+ des phrases importantes détectées

## Risques et mitigations

1. **Performance** : Calcul d'embeddings peut être lent
   - Mitigation : Cache des embeddings, traitement asynchrone

2. **Qualité segmentation** : Erreurs de segmentation possibles
   - Mitigation : Tests extensifs, ajustement des règles

3. **Faux positifs/négatifs** : Phrases importantes manquées ou phrases non importantes stockées
   - Mitigation : Ajustement des seuils, apprentissage continu

## Prochaines étapes immédiates

1. ✅ Architecture définie
2. ✅ Plan d'implémentation créé
3. ⏳ Commencer Phase 1 (Segmentation)
4. ⏳ Tests unitaires pour chaque phase
5. ⏳ Intégration progressive


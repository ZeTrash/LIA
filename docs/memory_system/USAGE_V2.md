# Guide d'utilisation - MemoryRank V2

## Vue d'ensemble

MemoryRank V2 traite les interactions en les segmentant en phrases, puis filtre et stocke uniquement les phrases importantes selon un score d'importance combiné.

## Utilisation basique

### Exemple simple

```python
from memory_service.phrase_memory_processor import PhraseMemoryProcessor
from memory_service.store import MemoryStore

# Créer le processeur
store = MemoryStore(use_memory_rank=True)
processor = PhraseMemoryProcessor(
    memory_store=store,
    alpha=0.4,      # Poids nouveauté
    beta=0.3,       # Poids RL
    gamma=0.3,      # Poids centralité
    threshold=0.5   # Seuil de stockage
)

# Traiter une interaction
interaction = {
    "prompt": "Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
    "response": "Python est effectivement un excellent choix.",
    "session_id": "session_123"
}

stored_ids = await processor.process_interaction(interaction)
print(f"{len(stored_ids)} phrases stockées")
```

## Configuration

### Paramètres du processeur

- **alpha** (0.4) : Poids pour la nouveauté
  - Plus élevé = favorise les phrases nouvelles
  - Plus bas = accepte plus de redondance

- **beta** (0.3) : Poids pour le lien RL
  - Utilité pour l'apprentissage par renforcement
  - Pour l'instant, valeur par défaut (0.5 = neutre)

- **gamma** (0.3) : Poids pour la centralité MemoryRank
  - Importance structurelle dans le graphe
  - Calculée automatiquement après stockage

- **threshold** (0.5) : Seuil d'importance pour stocker
  - Plus élevé = stocke moins de phrases (plus sélectif)
  - Plus bas = stocke plus de phrases (moins sélectif)

### Exemple de configuration

```python
# Configuration très sélective (peu de phrases stockées)
processor_selective = PhraseMemoryProcessor(
    threshold=0.7,
    alpha=0.5  # Favorise la nouveauté
)

# Configuration permissive (plus de phrases stockées)
processor_permissive = PhraseMemoryProcessor(
    threshold=0.3,
    alpha=0.3  # Accepte plus de redondance
)
```

## Pipeline de traitement

Le processeur exécute automatiquement :

1. **Segmentation** : Décompose prompt + response en phrases
2. **Récupération** : Récupère les souvenirs existants
3. **Filtrage** : Calcule l'importance de chaque phrase
4. **Stockage** : Stocke uniquement les phrases importantes
5. **Liens** : Crée des liens MemoryRank entre phrases co-occurrentes
6. **Ranking** : Recalcule les scores MemoryRank

## Résultats

### Accès aux phrases stockées

```python
# Récupérer le contexte (les phrases sont dans les souvenirs)
context = store.get_context(limit_memories=10)
memories = context.get("memories", [])

for memory in memories:
    print(f"Phrase: {memory['content']}")
    print(f"  Importance: {memory['importance_score']:.3f}")
    print(f"  MemoryRank: {memory.get('memory_rank_score', 0.0):.6f}")
```

### Statistiques

```python
# Après traitement de plusieurs interactions
context = store.get_context(limit_memories=100)
memories = context.get("memories", [])

print(f"Total phrases stockées: {len(memories)}")
print(f"Phrases avec MemoryRank élevé: {sum(1 for m in memories if m.get('memory_rank_score', 0) > 0.1)}")
```

## Avantages par rapport à V1

### V1 (Stockage brut)
```python
# Stocke le prompt entier
store.add_memory_from_interaction(
    content="Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
    importance_score=0.7
)
```

### V2 (Traitement par phrases)
```python
# Stocke automatiquement les phrases importantes séparément
# "Je préfère Python à Java" → stockée si importante
# "J'aime travailler sur des projets d'IA" → stockée si importante
# Phrases redondantes → filtrées automatiquement
```

## Intégration avec le système existant

### Utilisation dans LLMAdapter

```python
# Dans LLMAdapter, après génération d'une réponse
interaction = {
    "prompt": user_message,
    "response": generated_response,
    "session_id": session_id
}

# Traiter avec V2
if self.phrase_processor:
    await self.phrase_processor.process_interaction(interaction)
```

### Coexistence V1/V2

Les deux systèmes peuvent coexister :
- V1 : Stockage manuel de souvenirs complets
- V2 : Traitement automatique par phrases

## Exemples d'utilisation

Voir `examples/example_phrase_memory.py` pour un exemple complet.

## Dépannage

### Trop de phrases stockées
- Augmenter `threshold` (ex: 0.6 ou 0.7)
- Augmenter `alpha` pour favoriser la nouveauté

### Trop peu de phrases stockées
- Diminuer `threshold` (ex: 0.3 ou 0.4)
- Diminuer `alpha` pour accepter plus de redondance

### Phrases redondantes stockées
- Vérifier que les souvenirs existants sont bien récupérés
- Augmenter `alpha` pour favoriser la nouveauté


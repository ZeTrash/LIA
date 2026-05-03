# Intégration MemoryRank V2 avec LLMAdapter

## Activation

MemoryRank V2 peut être activé dans `LLMAdapter` via le paramètre `use_phrase_memory` :

```python
from core import LLMAdapter, CoreConfig

# Activer MemoryRank V2
adapter = LLMAdapter(
    config=CoreConfig(),
    use_memory=True,
    use_phrase_memory=True  # Active le traitement par phrases
)
```

## Fonctionnement automatique

Une fois activé, le système traite automatiquement chaque interaction :

1. **Génération de la réponse** (comme d'habitude)
2. **Journalisation de l'interaction** (comme d'habitude)
3. **Traitement par phrases** (nouveau) :
   - Segmentation en phrases
   - Filtrage sémantique
   - Stockage des phrases importantes
   - Création des liens MemoryRank

## Exemple complet

```python
from core import LLMAdapter, CoreConfig

# Configuration avec MemoryRank V2
adapter = LLMAdapter(
    config=CoreConfig(),
    use_memory=True,
    use_phrase_memory=True
)

# Générer une réponse (le traitement par phrases se fait automatiquement)
response = await adapter.generate(
    message="Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
    session_id="session_123"
)

# Les phrases importantes sont automatiquement stockées et liées
```

## Désactivation

Pour désactiver MemoryRank V2 tout en gardant la mémoire V1 :

```python
adapter = LLMAdapter(
    use_memory=True,
    use_phrase_memory=False  # Désactive V2, utilise V1 uniquement
)
```

## Coexistence V1/V2

Les deux systèmes peuvent coexister :

- **V1** : Stockage manuel via `memory.add_memory_from_interaction()`
- **V2** : Traitement automatique par phrases lors de chaque interaction

Les deux utilisent la même base de données et le même système MemoryRank pour les scores.

## Configuration avancée

Pour une configuration personnalisée du PhraseMemoryProcessor :

```python
from memory_service.phrase_memory_processor import PhraseMemoryProcessor
from memory_service.store import MemoryStore

# Créer un processeur personnalisé
store = MemoryStore(use_memory_rank=True)
processor = PhraseMemoryProcessor(
    memory_store=store,
    alpha=0.5,      # Plus de poids sur la nouveauté
    beta=0.2,       # Moins de poids sur RL
    gamma=0.3,      # Poids centralité
    threshold=0.6   # Seuil plus élevé (plus sélectif)
)

# L'utiliser manuellement
interaction = {
    "prompt": "...",
    "response": "...",
    "session_id": "..."
}
stored_ids = await processor.process_interaction(interaction)
```

## Logs

Le système affiche des logs pour suivre le traitement :

```
✅ PhraseMemoryProcessor (MemoryRank V2) activé
✅ [LLM_ADAPTER] Interaction journalisée
✅ [LLM_ADAPTER] 3 phrases stockées via MemoryRank V2
```

## Performance

Le traitement par phrases ajoute un léger overhead :
- **Segmentation** : < 10ms
- **Filtrage** : < 50ms (dépend du nombre de souvenirs existants)
- **Stockage** : < 20ms par phrase
- **Liens** : < 30ms par interaction

**Total estimé** : < 200ms par interaction (négligeable comparé à la génération LLM)

## Dépannage

### Le traitement ne se fait pas
- Vérifier que `use_phrase_memory=True`
- Vérifier les logs pour les erreurs
- Vérifier que `use_memory=True` aussi

### Trop de phrases stockées
- Augmenter le `threshold` dans PhraseMemoryProcessor
- Augmenter `alpha` pour favoriser la nouveauté

### Pas assez de phrases stockées
- Diminuer le `threshold`
- Vérifier que les souvenirs existants sont bien récupérés


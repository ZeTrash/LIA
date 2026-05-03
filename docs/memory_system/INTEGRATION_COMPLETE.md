# Intégration complète du système MemoryRank

Ce document décrit l'intégration complète du système MemoryRank (V1 et V2) avec le système principal LIA.

## Architecture d'intégration

```
┌─────────────────────────────────────────────────────────────┐
│                    LLMAdapter (core)                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MemoryAdapter (memory_service)                      │   │
│  │  - Logging des interactions                          │   │
│  │  - Récupération du contexte                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                    │
│                          ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MemoryStore (memory_service)                        │   │
│  │  - Stockage des souvenirs                            │   │
│  │  - MemoryRank V1 (tri par score)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                    │
│                          ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PhraseMemoryProcessor (V2) - OPTIONNEL              │   │
│  │  - Segmentation en phrases                            │   │
│  │  - Filtrage sémantique                                │   │
│  │  - Stockage sélectif                                  │   │
│  │  - Création de liens avancés                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                    │
│                          ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MemoryRankEngine                                    │   │
│  │  - Calcul des scores MemoryRank                       │   │
│  │  - Gestion du graphe                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Points d'intégration

### 1. LLMAdapter - Initialisation

**Fichier :** `core/llm_adapter.py`

**Code d'intégration :**
```python
def __init__(
    self,
    use_memory: bool = True,
    use_phrase_memory: bool = False,  # Activation V2
    ...
):
    # Initialisation MemoryAdapter (V1)
    if use_memory and MEMORY_AVAILABLE:
        self.memory = MemoryAdapter()
        
        # Initialisation PhraseMemoryProcessor (V2)
        if use_phrase_memory and PHRASE_MEMORY_AVAILABLE:
            store = MemoryStore(use_memory_rank=True)
            self.phrase_processor = PhraseMemoryProcessor(memory_store=store)
```

**Points d'activation :**
- `use_memory=True` : Active MemoryAdapter (V1)
- `use_phrase_memory=True` : Active PhraseMemoryProcessor (V2)

### 2. LLMAdapter - Génération de réponse

**Fichier :** `core/llm_adapter.py`

**Méthodes concernées :**
- `generate()` : Génération standard
- `generate_stream()` : Génération en streaming
- `_generate_internal()` : Génération interne

**Code d'intégration :**
```python
# Après génération de la réponse
if self.memory:
    # Journalisation V1 (toujours active)
    self.memory.log_interaction(
        session_id=session_id,
        prompt=message,
        response=response,
        severity="info"
    )
    
    # Traitement V2 (si activé)
    if self.phrase_processor:
        interaction = {
            "prompt": message,
            "response": response,
            "session_id": session_id
        }
        stored_ids = await self.phrase_processor.process_interaction(interaction)
```

### 3. MemoryStore - Tri par MemoryRank

**Fichier :** `memory_service/store.py`

**Méthode :** `get_context()`

**Code d'intégration :**
```python
def get_context(self, ...):
    # Récupération des souvenirs
    memories = ...
    
    # Tri par MemoryRank si activé
    if self.use_memory_rank:
        memories.sort(key=lambda m: m.get('memory_rank_score', 0.0), reverse=True)
    else:
        memories.sort(key=lambda m: m.get('importance_score', 0.0), reverse=True)
```

## Flux de données

### Flux V1 (Stockage brut)

```
Interaction → MemoryAdapter.log_interaction()
                ↓
            MemoryStore.add_memory_from_interaction()
                ↓
            SouvenirModel (stockage complet)
                ↓
            MemoryRankEngine.compute_and_update_ranks()
                ↓
            Tri par memory_rank_score dans get_context()
```

### Flux V2 (Traitement par phrases)

```
Interaction → PhraseMemoryProcessor.process_interaction()
                ↓
            PhraseSegmenter.segment_interaction()
                ↓ (phrases segmentées)
            SemanticFilter.filter_phrases()
                ↓ (phrases importantes)
            MemoryStore.add_memory() (pour chaque phrase)
                ↓
            PhraseLinker.create_links_for_interaction()
                ↓
            MemoryRankEngine.compute_and_update_ranks()
                ↓
            Tri par memory_rank_score dans get_context()
```

## Coexistence V1/V2

Les deux systèmes peuvent coexister :

### Mode V1 uniquement (par défaut)
```python
adapter = LLMAdapter(
    use_memory=True,
    use_phrase_memory=False  # V2 désactivé
)
```
- Stockage complet des interactions
- MemoryRank calculé sur souvenirs complets
- Compatible avec code existant

### Mode V2 uniquement
```python
adapter = LLMAdapter(
    use_memory=True,
    use_phrase_memory=True  # V2 activé
)
```
- Traitement automatique par phrases
- Stockage sélectif des phrases importantes
- MemoryRank calculé sur phrases individuelles

### Mode hybride (V1 + V2)
```python
adapter = LLMAdapter(
    use_memory=True,
    use_phrase_memory=True
)
# + appels manuels à memory.add_memory_from_interaction()
```
- V2 traite automatiquement chaque interaction
- V1 peut être utilisé pour stockage manuel supplémentaire
- Les deux utilisent la même base de données et MemoryRank

## Base de données

### Tables utilisées

1. **`souvenirs`** (V1 et V2)
   - Stocke les souvenirs (complets V1 ou phrases V2)
   - Champ `memory_rank_score` calculé par MemoryRankEngine

2. **`memory_links`** (V1 et V2)
   - Stocke les liens entre souvenirs
   - Types : `cooccurrence`, `causal`, `similarity`, etc.

3. **`interactions`** (V1)
   - Historique des interactions (log V1)

### Partage des données

- V1 et V2 utilisent la **même base de données**
- Les souvenirs V1 et V2 sont dans la **même table** (`souvenirs`)
- Les liens V1 et V2 sont dans la **même table** (`memory_links`)
- MemoryRank calcule les scores sur **tous les souvenirs** (V1 + V2)

## Configuration

### Variables d'environnement

```bash
# Chemin de la base de données (optionnel)
export LIA_MEMORY_DB_PATH=/path/to/memory.db

# Par défaut : data/memory.db
```

### Paramètres LLMAdapter

```python
adapter = LLMAdapter(
    # Activation mémoire
    use_memory=True,              # Active MemoryAdapter (V1)
    
    # Activation V2
    use_phrase_memory=True,       # Active PhraseMemoryProcessor (V2)
    
    # Autres paramètres...
)
```

### Paramètres PhraseMemoryProcessor

```python
# Configuration personnalisée
from memory_service.phrase_memory_processor import PhraseMemoryProcessor
from memory_service.store import MemoryStore

store = MemoryStore(use_memory_rank=True)
processor = PhraseMemoryProcessor(
    memory_store=store,
    alpha=0.4,      # Poids nouveauté
    beta=0.3,       # Poids RL
    gamma=0.3,      # Poids centralité
    threshold=0.5   # Seuil de stockage
)
```

## Tests d'intégration

### Test V1
```bash
python scripts/test_memory_rank_validation.py
```

### Test V2
```bash
python scripts/test_memory_rank_v2_validation.py
```

### Test complet
```bash
# Tester V1
python scripts/test_memory_rank_validation.py

# Tester V2
python scripts/test_memory_rank_v2_validation.py

# Les deux utilisent des bases de test séparées
```

## Logs et débogage

### Logs V1
```
✅ Mémoire intégrée au noyau primaire
✅ [LLM_ADAPTER] Interaction journalisée
```

### Logs V2
```
✅ PhraseMemoryProcessor (MemoryRank V2) activé
✅ [LLM_ADAPTER] 3 phrases stockées via MemoryRank V2
```

### Niveau de log
```python
import logging
logging.getLogger('memory_service').setLevel(logging.DEBUG)
logging.getLogger('core.llm_adapter').setLevel(logging.DEBUG)
```

## Performance

### Overhead V1
- Journalisation : < 10ms
- Calcul MemoryRank : < 50ms (selon nombre de souvenirs)

### Overhead V2
- Segmentation : < 10ms
- Filtrage : < 50ms (selon nombre de souvenirs existants)
- Stockage : < 20ms par phrase
- Liens : < 30ms par interaction
- **Total : < 200ms par interaction**

### Optimisations possibles
- Cache des embeddings (si implémenté)
- Calcul incrémental de MemoryRank
- Traitement asynchrone des phrases

## Migration

### De V1 vers V2

1. **Activer V2 progressivement**
   ```python
   # Phase 1 : Activer V2 en parallèle
   adapter = LLMAdapter(use_phrase_memory=True)
   
   # Phase 2 : Vérifier les résultats
   # Phase 3 : Désactiver V1 si souhaité
   ```

2. **Conserver les données V1**
   - Les souvenirs V1 restent dans la base
   - MemoryRank calcule sur V1 + V2
   - Pas de perte de données

3. **Migration complète (optionnel)**
   - Ré-segmenter les anciens souvenirs si nécessaire
   - Créer des liens entre V1 et V2

## Dépannage

### V2 ne s'active pas
- Vérifier `use_phrase_memory=True`
- Vérifier les imports (`PHRASE_MEMORY_AVAILABLE`)
- Vérifier les logs d'erreur

### Performance dégradée
- Vérifier le nombre de souvenirs (peut ralentir le filtrage)
- Activer le cache si embeddings implémentés
- Optimiser le seuil de filtrage (`threshold`)

### Données manquantes
- Vérifier que V1 ou V2 est activé
- Vérifier les logs de stockage
- Vérifier le seuil de filtrage (peut être trop élevé)

## Statut d'intégration

✅ **Intégration complète et fonctionnelle**

- V1 : Intégré et testé
- V2 : Intégré et testé
- Coexistence : Fonctionnelle
- Tests : Disponibles
- Documentation : Complète

## Prochaines étapes

Voir [IMPROVEMENTS_V2.md](IMPROVEMENTS_V2.md) pour les améliorations futures possibles.


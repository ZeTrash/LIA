# Architecture du système MemoryRank

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                         LIA Agent                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    LLMAdapter                                   │
│  (utilise MemoryAdapter pour récupérer le contexte mémoire)     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    MemoryAdapter                                 │
│  (interface simplifiée pour le noyau primaire)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    MemoryStore                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ use_memory_rank: bool = True (par défaut)                │  │
│  │ memory_rank_engine: MemoryRankEngine                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Méthodes principales :                                        │
│  - get_context() → utilise MemoryRank pour trier             │
│  - add_memory_link() → créer des liens                         │
│  - update_memory_ranks() → recalculer les scores              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
┌───────────────▼──────────┐  ┌──────────▼──────────────┐
│   MemoryRankEngine       │  │   Base de données       │
│                          │  │   (SQLite)               │
│  - add_link()            │  │                          │
│  - compute_and_update()  │  │  Tables :                │
│  - detect_cooccurrence() │  │  - souvenirs             │
│                          │  │  - memory_links          │
└───────────────┬──────────┘  │  - traits                │
                │             │  - interaction_logs       │
                │             └──────────────────────────┘
                │
┌───────────────▼──────────┐
│   MemoryRank             │
│   (Algorithme PageRank)  │
│                          │
│  - compute_ranks()       │
│  - temporal_decay()      │
│  - hybrid_score()        │
└──────────────────────────┘
```

## Flux de données

### 1. Création de souvenirs et liens

```
Utilisateur/Agent
    │
    ├─→ MemoryStore.add_memory()
    │       │
    │       └─→ SouvenirModel (DB)
    │
    └─→ MemoryStore.add_memory_link()
            │
            └─→ MemoryRankEngine.add_link()
                    │
                    └─→ MemoryLinkModel (DB)
```

### 2. Calcul des scores MemoryRank

```
MemoryStore.get_context()
    │
    ├─→ MemoryRankEngine.compute_and_update_ranks()
    │       │
    │       ├─→ get_memory_graph()
    │       │       │
    │       │       ├─→ SouvenirModel (récupérer tous les souvenirs)
    │       │       └─→ MemoryLinkModel (récupérer tous les liens)
    │       │
    │       ├─→ MemoryRank.compute_ranks()
    │       │       │
    │       │       ├─→ Construire matrice de transition M
    │       │       ├─→ Normaliser les colonnes
    │       │       └─→ Itérer jusqu'à convergence
    │       │
    │       └─→ Mettre à jour SouvenirModel.memory_rank_score
    │
    └─→ get_top_memories_by_rank()
            │
            └─→ Retourner souvenirs triés par memory_rank_score
```

### 3. Détection automatique de co-occurrences

```
MemoryRankEngine.detect_cooccurrence_links()
    │
    ├─→ InteractionModel (récupérer interactions récentes)
    │
    ├─→ Pour chaque interaction :
    │       │
    │       ├─→ Analyser prompt et response
    │       │
    │       ├─→ Identifier souvenirs mentionnés
    │       │
    │       └─→ Créer liens cooccurrence entre tous les souvenirs
    │               mentionnés ensemble
    │
    └─→ MemoryLinkModel (sauvegarder les liens)
```

## Structure des données

### Modèle SouvenirModel

```
SouvenirModel
├── memory_id (PK)
├── category
├── content
├── tags
├── importance_score      ← Score d'importance classique
├── recency_score         ← Score de récence
├── emotion_score
├── memory_rank_score     ← NOUVEAU : Score MemoryRank
├── frequency
├── ttl
├── created_at
└── updated_at
```

### Modèle MemoryLinkModel

```
MemoryLinkModel
├── link_id (PK)
├── source_memory_id (FK → SouvenirModel)
├── target_memory_id (FK → SouvenirModel)
├── weight                ← Force de référence (wij)
├── link_type             ← cooccurrence, similarity, citation, etc.
├── metadata              ← Métadonnées additionnelles (JSON)
├── created_at
└── updated_at
```

## Graphe de mémoire

### Représentation

```
Souvenir A (memory_rank_score: 0.15)
    │
    ├─→ [weight: 1.0, type: cooccurrence] → Souvenir B (score: 0.20)
    │
    └─→ [weight: 0.5, type: similarity] → Souvenir C (score: 0.10)
            │
            └─→ [weight: 1.0, type: citation] → Souvenir D (score: 0.25)
```

### Calcul du score

Pour Souvenir B :
```
R_B = (1 - 0.85) + 0.85 * [
    (w_AB / Σ_k w_Ak) * R_A +
    (w_CB / Σ_k w_Ck) * R_C +
    ...
]
```

## Extensions

### Hiérarchie fractale

```
Niveau OBJECTIVE (objectifs/buts)
    │
    ├─→ Niveau CONCEPT (concepts abstraits)
    │       │
    │       ├─→ Niveau EPISODE (groupes d'événements)
    │       │       │
    │       │       └─→ Niveau EVENT (événements individuels)
    │       │
    │       └─→ Niveau EPISODE
    │
    └─→ Niveau CONCEPT
```

Chaque niveau a son propre graphe et ses propres scores MemoryRank.

### Intégration RL

```
Agent RL
    │
    ├─→ Action → Récompense
    │       │
    │       └─→ RLMemoryRank.update_memory_with_reward()
    │               │
    │               └─→ Mise à jour importance_score (proxy pour reward)
    │
    └─→ compute_hybrid_ranks()
            │
            ├─→ MemoryRank (structurel)
            ├─→ Reward (utilité RL)
            └─→ Similarity (sémantique)
                    │
                    └─→ Score hybride final
```

## Interactions entre composants

### MemoryStore ↔ MemoryRankEngine

```
MemoryStore
    │
    ├─→ get_context()
    │       └─→ memory_rank_engine.compute_and_update_ranks()
    │
    ├─→ add_memory_link()
    │       └─→ memory_rank_engine.add_link()
    │
    └─→ update_memory_ranks()
            └─→ memory_rank_engine.compute_and_update_ranks()
```

### MemoryRankEngine ↔ MemoryRank

```
MemoryRankEngine
    │
    ├─→ compute_and_update_ranks()
    │       │
    │       ├─→ Récupérer graphe (souvenirs + liens)
    │       │
    │       └─→ memory_rank.compute_ranks(memory_ids, links)
    │               │
    │               └─→ Retourne {memory_id: rank_score}
    │
    └─→ compute_and_update_ranks(use_temporal_decay=True)
            │
            └─→ memory_rank.compute_ranks_with_temporal_decay(...)
```

## Séquence d'exécution typique

### Scénario : Récupération du contexte

```
1. LLMAdapter.generate()
    │
2. MemoryAdapter.get_context()
    │
3. MemoryStore.get_context()
    │
4. [Si MemoryRank activé]
    │
    ├─→ MemoryRankEngine.compute_and_update_ranks()
    │       │
    │       ├─→ get_memory_graph()
    │       │       ├─→ SELECT * FROM souvenirs WHERE ttl > NOW()
    │       │       └─→ SELECT * FROM memory_links WHERE ...
    │       │
    │       ├─→ MemoryRank.compute_ranks()
    │       │       ├─→ Construire matrice M (n×n)
    │       │       ├─→ Normaliser colonnes
    │       │       └─→ Itérer jusqu'à convergence
    │       │
    │       └─→ UPDATE souvenirs SET memory_rank_score = ... WHERE ...
    │
5. MemoryRankEngine.get_top_memories_by_rank()
    │
    └─→ SELECT * FROM souvenirs WHERE ... ORDER BY memory_rank_score DESC
```

## Points d'extension

### 1. Nouveaux types de liens

Ajouter dans `MemoryLinkModel.link_type` :
- `temporal` : Lien temporel (avant/après)
- `spatial` : Lien spatial (localisation)
- `emotional` : Lien émotionnel

### 2. Nouveaux algorithmes de ranking

Créer une nouvelle classe héritant de `MemoryRank` :
```python
class WeightedMemoryRank(MemoryRank):
    def compute_ranks(self, ...):
        # Implémentation personnalisée
        pass
```

### 3. Nouveaux niveaux hiérarchiques

Ajouter dans `MemoryLevel` :
```python
class MemoryLevel(Enum):
    # ... existants
    DOMAIN = "domain"  # Nouveau niveau
```

## Performance

### Complexité

- **Temps :** O(E × itérations) où E = nombre de liens
- **Espace :** O(n²) pour la matrice (n = nombre de souvenirs)

### Optimisations actuelles

- Calcul offline (pas en temps réel)
- Graphe sparse (peu de liens par souvenir)
- Cache des scores dans la base de données

### Optimisations futures

- Matrice sparse (scipy.sparse)
- Calcul incrémental
- Calcul asynchrone
- Partitionnement par niveau hiérarchique


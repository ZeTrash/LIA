# Guide de démarrage rapide - MemoryRank

Ce guide vous permet de commencer rapidement avec le système MemoryRank.

## Installation

```bash
cd /opt/LIA
source venv/bin/activate
pip install -r memory_service/requirements.txt
```

## Utilisation basique

### 1. Créer des souvenirs

```python
from memory_service.store import MemoryStore

store = MemoryStore()

# Créer quelques souvenirs
mem1 = store.add_memory(
    category="fact",
    content="L'utilisateur préfère Python à Java",
    importance_score=0.8
)

mem2 = store.add_memory(
    category="fact",
    content="L'utilisateur travaille sur un projet d'IA",
    importance_score=0.7
)
```

### 2. Créer des liens entre souvenirs

```python
# Créer un lien de co-occurrence
link_id = store.add_memory_link(
    source_memory_id=mem1,
    target_memory_id=mem2,
    weight=1.0,
    link_type="cooccurrence"
)
```

### 3. Calculer les scores MemoryRank

```python
# Mettre à jour les scores
ranks = store.update_memory_ranks()

print(f"Scores calculés pour {len(ranks)} souvenirs")
for memory_id, score in ranks.items():
    print(f"  {memory_id}: {score:.4f}")
```

### 4. Récupérer le contexte (avec MemoryRank)

```python
# Récupérer le contexte (souvenirs triés par MemoryRank)
context = store.get_context(limit_memories=10)

for memory in context["memories"]:
    print(f"Score MemoryRank: {memory['memory_rank_score']:.4f}")
    print(f"Contenu: {memory['content']}")
```

## Détection automatique de co-occurrences

Le système peut détecter automatiquement les co-occurrences dans les interactions :

```python
from memory_service.memory_rank_engine import MemoryRankEngine

engine = MemoryRankEngine()

# Détecter les co-occurrences dans les 7 derniers jours
links_created = engine.detect_cooccurrence_links(lookback_days=7)
print(f"{links_created} liens créés automatiquement")

# Recalculer les scores
engine.compute_and_update_ranks()
```

## Exemple complet

```python
from memory_service.store import MemoryStore
from memory_service.memory_rank_engine import MemoryRankEngine

# Initialiser
store = MemoryStore()
engine = MemoryRankEngine()

# 1. Créer des souvenirs
memories = []
for i in range(5):
    mem_id = store.add_memory(
        category="fact",
        content=f"Information importante {i}",
        importance_score=0.5 + i * 0.1
    )
    memories.append(mem_id)

# 2. Créer des liens (graphe en étoile)
for i in range(1, len(memories)):
    store.add_memory_link(
        source_memory_id=memories[0],
        target_memory_id=memories[i],
        weight=1.0,
        link_type="cooccurrence"
    )

# 3. Calculer les scores
ranks = store.update_memory_ranks()

# 4. Récupérer les souvenirs les plus importants
context = store.get_context(limit_memories=5)

print("Top souvenirs par MemoryRank:")
for i, memory in enumerate(context["memories"], 1):
    print(f"{i}. Score: {memory['memory_rank_score']:.4f}")
    print(f"   Contenu: {memory['content']}")
```

## Intégration avec le système existant

MemoryRank est automatiquement utilisé par `MemoryAdapter` via `MemoryStore` :

```python
from memory_service.memory_adapter import MemoryAdapter

adapter = MemoryAdapter()

# Le contexte récupéré utilise MemoryRank par défaut
context = adapter.get_context(limit_memories=10)

# Les souvenirs sont triés par memory_rank_score
for memory in context["memories"]:
    print(f"MemoryRank: {memory.get('memory_rank_score', 0.0):.4f}")
```

## Désactiver MemoryRank

Si vous voulez revenir à l'ancien système (tri par importance_score + recency_score) :

```python
store = MemoryStore(use_memory_rank=False)
```

## Prochaines étapes

- Lire la [documentation complète](README.md)
- Consulter les [détails d'implémentation](IMPLEMENTATION.md)
- Explorer le [concept théorique](concept.md)
- Exécuter les [tests](../memory_service/tests/test_memory_rank.py)


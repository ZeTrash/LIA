# Système MemoryRank

## Vue d'ensemble

MemoryRank est un système de ranking de mémoire pour agents autonomes, basé sur la transposition de l'algorithme PageRank à la gestion de mémoire. Le principe fondamental est que **un souvenir est important si d'autres souvenirs importants le référencent**.

## Versions

### MemoryRank V1 (Stockage brut)
- Stockage complet des interactions
- Calcul MemoryRank sur les souvenirs complets
- Liens manuels ou automatiques (co-occurrence)

### MemoryRank V2 (Traitement par phrases) ⭐ **NOUVEAU**
- Segmentation automatique en phrases
- Filtrage sémantique intelligent
- Stockage sélectif des phrases importantes
- Création automatique de liens avancés
- **Activation** : `LLMAdapter(use_phrase_memory=True)`

Voir [USAGE_V2.md](USAGE_V2.md) et [INTEGRATION_V2.md](INTEGRATION_V2.md) pour plus de détails.

## Architecture

### Composants principaux V1

1. **Modèles de données** (`models.py`)
   - `SouvenirModel` : Stocke les souvenirs avec un champ `memory_rank_score`
   - `MemoryLinkModel` : Stocke les liens entre souvenirs (graphe de mémoire)

2. **Algorithme MemoryRank** (`memory_rank.py`)
   - Implémentation de l'algorithme PageRank adapté pour la mémoire
   - Support de la décroissance temporelle
   - Calcul de scores hybrides (MemoryRank + Reward + Similarité)

3. **Moteur MemoryRank** (`memory_rank_engine.py`)
   - Gestion du graphe de mémoire
   - Calcul et mise à jour des scores
   - Détection automatique de co-occurrences

4. **Extensions avancées** (`memory_rank_extensions.py`)
   - Hiérarchie fractale (événements → épisodes → concepts → objectifs)
   - Intégration avec récompenses RL

5. **Intégration** (`store.py`)
   - `MemoryStore` utilise MemoryRank pour trier les souvenirs
   - Méthodes pour créer des liens et mettre à jour les scores

### Composants V2 (Traitement par phrases)

1. **Segmentation** (`phrase_segmenter.py`)
   - Détection automatique des limites de phrases
   - Filtrage des phrases non informatives

2. **Filtrage sémantique** (`semantic_filter.py`)
   - Calcul de nouveauté (similarité avec souvenirs existants)
   - Score d'importance : `I = α·nouveauté + β·RL + γ·centralité`

3. **Score RL** (`rl_scorer.py`)
   - Calcul de l'utilité pour l'apprentissage par renforcement
   - Historique des récompenses avec décroissance temporelle

4. **Création de liens** (`phrase_linker.py`)
   - Liens de co-occurrence automatiques
   - Détection de dépendances causales
   - Liens de similarité sémantique

5. **Processeur principal** (`phrase_memory_processor.py`)
   - Orchestration du pipeline complet
   - Intégration avec MemoryRank V1

## Formule MemoryRank

```
R_j = (1 - d) + d * Σ_i (w_ij / Σ_k w_ik) * R_i
```

où :
- `R_j` = importance du souvenir j
- `d` = facteur d'amortissement (≈ 0.85)
- `w_ij` = poids du lien du souvenir i vers j
- `Σ_k w_ik` = somme des poids des liens sortants de i

## Utilisation

### Activation de MemoryRank

MemoryRank est activé par défaut dans `MemoryStore`. Pour le désactiver :

```python
from memory_service.store import MemoryStore

store = MemoryStore(use_memory_rank=False)
```

### Création de liens entre souvenirs

```python
# Créer un lien de co-occurrence
link_id = store.add_memory_link(
    source_memory_id="mem_1",
    target_memory_id="mem_2",
    weight=1.0,
    link_type="cooccurrence"
)
```

### Mise à jour des scores

```python
# Calculer et mettre à jour les scores MemoryRank
ranks = store.update_memory_ranks()
```

### Utilisation directe du moteur

```python
from memory_service.memory_rank_engine import MemoryRankEngine

engine = MemoryRankEngine()
ranks = engine.compute_and_update_ranks()
```

### Détection automatique de co-occurrences

```python
# Détecter les co-occurrences dans les interactions récentes
links_created = engine.detect_cooccurrence_links(lookback_days=7)
```

## Extensions

### Décroissance temporelle

Pour activer la décroissance temporelle :

```python
engine = MemoryRankEngine(use_temporal_decay=True, decay_factor=0.01)
ranks = engine.compute_and_update_ranks()
```

### Hiérarchie fractale

```python
from memory_service.memory_rank_extensions import FractalMemoryRank, MemoryLevel

fractal = FractalMemoryRank()
ranks = fractal.compute_hierarchical_ranks(MemoryLevel.CONCEPT)
```

### Intégration RL

```python
from memory_service.memory_rank_extensions import RLMemoryRank

rl_rank = RLMemoryRank()
rl_rank.update_memory_with_reward(memory_id="mem_1", reward=0.8)
```

## Types de liens

Les types de liens supportés incluent :
- `cooccurrence` : Souvenirs mentionnés ensemble
- `similarity` : Similarité sémantique (embeddings)
- `citation` : Citation explicite
- `causal` : Dépendance causale (RL)
- `hierarchical` : Lien hiérarchique (fractal)

## Tests

Exécuter les tests :

```bash
cd /opt/LIA
source venv/bin/activate
pytest memory_service/tests/test_memory_rank.py -v
```

## Migration de la base de données

Le nouveau modèle `MemoryLinkModel` et le champ `memory_rank_score` seront automatiquement créés lors de la prochaine utilisation. Pour forcer la création :

```python
from memory_service.db import get_db
from memory_service.models import Base

db = get_db()
Base.metadata.create_all(db.engine)
```

## Performance

- **Complexité** : O(E × itérations) où E est le nombre de liens
- **Optimisations** :
  - Calcul incrémental possible
  - Graphe sparse (peu de liens par souvenir)
  - Calcul offline périodique

## Limitations et risques

1. **Boucle d'auto-renforcement** : Les souvenirs centraux peuvent devenir encore plus centraux
   - Solution : Bruit exploratoire, oubli aléatoire contrôlé, recalcul périodique

2. **Coût computationnel** : Avec des millions de souvenirs, le calcul peut être coûteux
   - Solution : Calcul offline, graphe sparse, mise à jour incrémentale

## Documentation

La documentation complète du système MemoryRank est organisée en plusieurs documents :

### MemoryRank V1 (Stockage brut)

1. **[Concept](concept.md)** - Description conceptuelle et théorique du système V1
2. **[Implémentation](IMPLEMENTATION.md)** - Détails techniques, architecture et choix d'implémentation V1
3. **[Architecture](ARCHITECTURE.md)** - Diagrammes et structure du système V1
4. **[Guide de démarrage rapide](QUICK_START.md)** - Exemples pratiques pour commencer
5. **[Changelog](CHANGELOG.md)** - Liste complète des fichiers créés et modifiés

### MemoryRank V2 (Traitement par phrases) ⭐

6. **[Concept V2](concept_v2.md)** - Nouvelle approche : segmentation en phrases et filtrage sémantique
7. **[Architecture V2](ARCHITECTURE_V2.md)** - Architecture détaillée du système V2
8. **[Plan d'implémentation V2](IMPLEMENTATION_PLAN_V2.md)** - Plan détaillé phase par phase pour implémenter V2
9. **[Guide d'utilisation V2](USAGE_V2.md)** - Guide complet d'utilisation du système V2
10. **[Intégration V2](INTEGRATION_V2.md)** - Guide d'intégration avec LLMAdapter
11. **[État d'implémentation V2](STATUS_V2.md)** - État actuel de l'implémentation V2
12. **[Améliorations futures V2](IMPROVEMENTS_V2.md)** - Liste des améliorations possibles

### Intégration complète

13. **[Intégration complète](INTEGRATION_COMPLETE.md)** - Documentation complète de l'intégration V1+V2 avec le système principal

### Tests

- **[Tests V1](../../scripts/test_memory_rank_validation.py)** - Script de validation complet pour V1
- **[Tests V2](../../scripts/test_memory_rank_v2_validation.py)** - Script de validation complet pour V2
- **[README Tests V1](../../scripts/README_MEMORY_RANK_TEST.md)** - Documentation des tests V1
- **[README Tests V2](../../scripts/README_MEMORY_RANK_V2_TEST.md)** - Documentation des tests V2

## Références

Voir `docs/memory_system/concept.md` pour la description conceptuelle complète du système MemoryRank.
Voir `docs/memory_system/IMPLEMENTATION.md` pour les détails d'implémentation et les choix techniques.


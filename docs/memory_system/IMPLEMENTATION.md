# Documentation d'implémentation - Système MemoryRank

## Vue d'ensemble

Ce document décrit l'implémentation complète du système MemoryRank, une transposition de l'algorithme PageRank pour la gestion de mémoire d'un agent autonome.

## Architecture générale

Le système MemoryRank est composé de plusieurs couches :

```
┌─────────────────────────────────────────────────────────┐
│                    MemoryStore                          │
│  (Interface principale, utilise MemoryRank par défaut)   │
└────────────────────┬──────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────┐
│              MemoryRankEngine                          │
│  (Gestion du graphe, calcul et mise à jour des scores) │
└────────────────────┬──────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────┐
│                 MemoryRank                             │
│  (Algorithme PageRank pur, calcul des rangs)           │
└────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│           MemoryRankExtensions                         │
│  (Hiérarchie fractale, intégration RL)                 │
└─────────────────────────────────────────────────────────┘
```

## Composants implémentés

### 1. Modèles de données (`models.py`)

#### Ajout de `memory_rank_score` dans `SouvenirModel`

**Pourquoi :** Stocker le score MemoryRank calculé directement dans le modèle pour éviter les recalculs fréquents.

**Comment :**
```python
memory_rank_score: Mapped[float] = mapped_column(Float, default=0.0)
```

- Type : `Float` avec valeur par défaut `0.0`
- Mise à jour : Automatique lors du calcul MemoryRank
- Utilisation : Tri des souvenirs dans `get_context()`

#### Création de `MemoryLinkModel`

**Pourquoi :** Représenter le graphe de mémoire avec des liens pondérés entre souvenirs.

**Structure :**
```python
class MemoryLinkModel(Base):
    link_id: str                    # Identifiant unique
    source_memory_id: str           # Souvenir source (FK)
    target_memory_id: str           # Souvenir cible (FK)
    weight: float                   # Force de référence (wij)
    link_type: str                  # Type de lien
    metadata: dict                   # Métadonnées additionnelles
    created_at: datetime
    updated_at: datetime
```

**Types de liens supportés :**
- `cooccurrence` : Souvenirs mentionnés ensemble dans une interaction
- `similarity` : Similarité sémantique (basée sur embeddings)
- `citation` : Citation explicite d'un souvenir par un autre
- `causal` : Dépendance causale (dans un contexte RL)
- `hierarchical` : Lien hiérarchique (pour la mémoire fractale)

**Contraintes :**
- Clé primaire : `link_id`
- Clés étrangères : `source_memory_id` et `target_memory_id` vers `souvenirs.memory_id`
- Pas de contrainte d'unicité sur (source, target, type) : permet plusieurs liens du même type avec poids différents (fusionnés par moyenne)

### 2. Algorithme MemoryRank (`memory_rank.py`)

#### Classe `MemoryRank`

**Implémentation de la formule PageRank :**

```python
R_j = (1 - d) + d * Σ_i (w_ij / Σ_k w_ik) * R_i
```

**Détails d'implémentation :**

1. **Construction de la matrice de transition M (n×n)**
   - `M[j][i] = w_ij` : Poids du lien de i vers j
   - Note : `M[j][i]` car on veut la transposée pour PageRank

2. **Normalisation des colonnes**
   ```python
   column_sums = M.sum(axis=0)
   column_sums[column_sums == 0] = 1.0  # Éviter division par zéro
   M = M / column_sums
   ```
   - Chaque colonne i représente les liens sortants du souvenir i
   - Normalisation : diviser par la somme totale des poids sortants
   - Téléportation : si un souvenir n'a pas de liens sortants, utiliser distribution uniforme (1/n)

3. **Itération de PageRank**
   ```python
   ranks = np.ones(n) / n  # Initialisation uniforme
   for iteration in range(max_iterations):
       new_ranks = (1 - d) / n + d * M @ ranks
       if convergence:
           break
       ranks = new_ranks
   ```
   - Facteur d'amortissement `d = 0.85` (standard PageRank)
   - Convergence : arrêt si `max(|new_ranks - ranks|) < tolerance`

**Complexité :**
- Temps : O(E × itérations) où E est le nombre de liens
- Espace : O(n²) pour la matrice (peut être optimisé en sparse)

#### Extension temporelle

**Formule :**
```python
R_j(t) = R_j * e^(-λ * t)
```

**Implémentation :**
- Calcul des rangs de base avec `compute_ranks()`
- Application de la décroissance exponentielle par âge
- Paramètre `decay_factor` (λ) : contrôle la vitesse de décroissance

**Utilisation :**
```python
ranks = memory_rank.compute_ranks_with_temporal_decay(
    memory_ids, links, memory_ages, decay_factor=0.01
)
```

#### Score hybride

**Formule :**
```python
Score = α * MemoryRank + β * Reward + γ * Similarité
```

**Normalisation :**
- Les poids (α, β, γ) sont normalisés pour sommer à 1.0
- Si un composant est absent, les poids sont ajustés proportionnellement

### 3. Moteur MemoryRank (`memory_rank_engine.py`)

#### Classe `MemoryRankEngine`

**Responsabilités :**
1. Gestion du graphe de mémoire (ajout/suppression de liens)
2. Calcul et mise à jour des scores MemoryRank
3. Récupération des souvenirs triés par MemoryRank
4. Détection automatique de co-occurrences

#### Méthode `add_link()`

**Logique :**
1. Vérifier l'existence des souvenirs source et cible
2. Chercher un lien existant du même type
3. Si existant : mettre à jour le poids (moyenne avec l'ancien)
4. Sinon : créer un nouveau lien

**Fusion de poids :**
```python
existing.weight = (existing.weight + weight) / 2.0
```
- Stratégie : moyenne simple (peut être améliorée avec pondération temporelle)

#### Méthode `compute_and_update_ranks()`

**Processus :**
1. Récupérer le graphe complet (`get_memory_graph()`)
2. Calculer les rangs avec `MemoryRank.compute_ranks()`
3. Mettre à jour `memory_rank_score` pour chaque souvenir
4. Commit de la transaction

**Optimisation future :**
- Vérifier la dernière mise à jour pour éviter les recalculs inutiles
- Calcul incrémental pour les nouveaux liens seulement

#### Méthode `detect_cooccurrence_links()`

**Algorithme :**
1. Récupérer les interactions récentes (paramètre `lookback_days`)
2. Pour chaque interaction :
   - Extraire le prompt et la réponse
   - Chercher les souvenirs mentionnés (par contenu ou tags)
   - Créer des liens entre tous les souvenirs co-mentionnés
3. Retourner le nombre de liens créés

**Limitations actuelles :**
- Recherche simple par substring (peut être améliorée avec embeddings)
- Pas de détection de similarité sémantique

### 4. Intégration dans MemoryStore (`store.py`)

#### Modification de `__init__()`

**Ajout :**
```python
def __init__(self, db: Optional[Database] = None, use_memory_rank: bool = True):
    self.use_memory_rank = use_memory_rank
    self.memory_rank_engine = MemoryRankEngine(db=self.db) if use_memory_rank else None
```

**Choix :** MemoryRank activé par défaut pour bénéficier immédiatement des améliorations.

#### Modification de `get_context()`

**Ancien système :**
```python
memories = session.query(SouvenirModel).filter(
    SouvenirModel.ttl > datetime.now(UTC)
).order_by(
    desc(SouvenirModel.importance_score),
    desc(SouvenirModel.recency_score)
).limit(limit_memories).all()
```

**Nouveau système :**
```python
if self.use_memory_rank and self.memory_rank_engine:
    self.memory_rank_engine.compute_and_update_ranks()
    memories = self.memory_rank_engine.get_top_memories_by_rank(
        limit=limit_memories, include_expired=False
    )
else:
    # Fallback sur l'ancien système
    ...
```

**Gestion d'erreurs :** Fallback automatique sur l'ancien système en cas d'erreur.

#### Ajout de méthodes utilitaires

**`add_memory_link()` :** Wrapper autour de `MemoryRankEngine.add_link()`

**`update_memory_ranks()` :** Wrapper autour de `MemoryRankEngine.compute_and_update_ranks()`

### 5. Extensions avancées (`memory_rank_extensions.py`)

#### Hiérarchie fractale (`FractalMemoryRank`)

**Concept :** Calculer MemoryRank séparément pour chaque niveau hiérarchique.

**Niveaux :**
- `EVENT` : Événements individuels
- `EPISODE` : Groupes d'événements
- `CONCEPT` : Concepts abstraits
- `OBJECTIVE` : Objectifs/buts

**Implémentation actuelle :**
- Identification du niveau basée sur les tags (heuristique simple)
- Calcul séparé pour chaque niveau
- Lien hiérarchique : `create_hierarchical_link()` pour connecter les niveaux

**Amélioration future :**
- Classification automatique du niveau avec ML
- Propagation des scores entre niveaux

#### Intégration RL (`RLMemoryRank`)

**Fonctionnalités :**
1. **Score hybride :** Combine MemoryRank + Reward + Similarité
2. **Mise à jour avec récompense :** `update_memory_with_reward()`

**Formule de mise à jour :**
```python
new_importance = current_importance * decay_factor + reward * (1 - decay_factor)
```
- Décroissance exponentielle des récompenses anciennes
- Stockage dans `importance_score` (provisoire, devrait avoir un champ dédié)

**Limitation actuelle :** Utilise `importance_score` comme proxy pour `reward_score`. Un champ dédié serait préférable.

## Flux de données

### Calcul initial des scores

```
1. Création de souvenirs → SouvenirModel
2. Création de liens → MemoryLinkModel
3. Appel compute_and_update_ranks()
   ├─ Récupération du graphe (souvenirs + liens)
   ├─ Calcul MemoryRank
   └─ Mise à jour memory_rank_score
4. get_context() utilise memory_rank_score pour trier
```

### Détection automatique de co-occurrences

```
1. Interaction utilisateur → InteractionModel
2. Appel detect_cooccurrence_links()
   ├─ Analyse des interactions récentes
   ├─ Détection de mentions de souvenirs
   └─ Création de liens cooccurrence
3. Recalcul automatique des scores (optionnel)
```

## Choix d'implémentation

### 1. Utilisation de NumPy

**Pourquoi :**
- Calcul matriciel efficace pour PageRank
- Opérations vectorisées optimisées

**Alternative considérée :** Implémentation pure Python (rejetée pour performance)

### 2. Matrice dense vs sparse

**Choix actuel :** Matrice dense NumPy

**Raison :** Simplicité et performance acceptable pour des milliers de souvenirs

**Optimisation future :** Utiliser `scipy.sparse` pour des millions de souvenirs

### 3. Calcul synchrone vs asynchrone

**Choix actuel :** Calcul synchrone dans `get_context()`

**Impact :** Peut ralentir la récupération du contexte si le graphe est grand

**Optimisation future :** Calcul asynchrone en arrière-plan, cache des scores

### 4. Fusion de poids de liens

**Choix actuel :** Moyenne simple `(old + new) / 2`

**Alternatives considérées :**
- Moyenne pondérée par temps
- Maximum (garder le poids le plus fort)
- Somme (accumulation)

**Raison :** Simplicité, peut être amélioré selon les besoins

### 5. Détection de co-occurrences

**Choix actuel :** Recherche par substring

**Limitations :**
- Ne détecte pas les synonymes
- Sensible à la casse et à la ponctuation

**Amélioration future :** Utiliser des embeddings pour similarité sémantique

## Tests

### Structure des tests (`tests/test_memory_rank.py`)

**Tests unitaires :**
1. `test_memory_rank_basic` : Algorithme PageRank de base
2. `test_memory_rank_engine_add_link` : Création de liens
3. `test_memory_rank_engine_compute_ranks` : Calcul et mise à jour
4. `test_memory_store_with_memory_rank` : Intégration dans MemoryStore
5. `test_memory_rank_temporal_decay` : Décroissance temporelle
6. `test_hybrid_score` : Score hybride
7. `test_fractal_memory_rank` : Hiérarchie fractale
8. `test_rl_memory_rank` : Intégration RL

**Fixtures :**
- `temp_db` : Base de données temporaire pour isolation des tests
- `sample_memories` : Souvenirs de test

## Migration de la base de données

### Changements de schéma

1. **Table `souvenirs` :**
   - Ajout de la colonne `memory_rank_score` (Float, default=0.0)

2. **Nouvelle table `memory_links` :**
   - Création automatique par SQLAlchemy via `Base.metadata.create_all()`

### Compatibilité

- **Rétrocompatibilité :** Les anciens souvenirs ont `memory_rank_score = 0.0`
- **Fallback :** Si MemoryRank échoue, utilisation de l'ancien système de tri
- **Migration automatique :** Pas de script de migration nécessaire, SQLAlchemy gère

## Performance et optimisations

### Mesures actuelles

- **Complexité temporelle :** O(E × itérations) où E = nombre de liens
- **Complexité spatiale :** O(n²) pour la matrice (n = nombre de souvenirs)
- **Convergence :** Généralement < 100 itérations pour tolérance 1e-6

### Optimisations implémentées

1. **Graphe sparse :** Peu de liens par souvenir → matrice principalement nulle
2. **Calcul offline :** Peut être exécuté périodiquement en arrière-plan
3. **Cache :** Les scores sont stockés dans la base de données

### Optimisations futures

1. **Matrice sparse :** Utiliser `scipy.sparse.csr_matrix` pour grandes échelles
2. **Calcul incrémental :** Mise à jour seulement des scores affectés par nouveaux liens
3. **Calcul asynchrone :** Background task pour recalcul périodique
4. **Indexation :** Index sur `memory_rank_score` pour tri rapide
5. **Partitionnement :** Calcul par niveau hiérarchique (fractal)

## Limitations connues

### 1. Boucle d'auto-renforcement

**Problème :** Les souvenirs centraux deviennent encore plus centraux.

**Solutions partielles :**
- Décroissance temporelle
- Recalcul périodique

**Solutions futures :**
- Bruit exploratoire (ajout de liens aléatoires)
- Oubli aléatoire contrôlé
- Seuil de saturation pour les scores

### 2. Coût computationnel

**Problème :** Avec des millions de souvenirs, le calcul peut être lent.

**Solutions futures :**
- Matrice sparse
- Calcul incrémental
- Approximation (échantillonnage)

### 3. Détection de co-occurrences

**Problème :** Recherche par substring est limitée.

**Solution future :** Utiliser des embeddings pour similarité sémantique.

### 4. Identification du niveau hiérarchique

**Problème :** Heuristique basée sur tags est fragile.

**Solution future :** Classification automatique avec ML.

## Utilisation recommandée

### Configuration initiale

```python
from memory_service.store import MemoryStore

# MemoryRank activé par défaut
store = MemoryStore()

# Ou explicitement
store = MemoryStore(use_memory_rank=True)
```

### Création de liens

```python
# Manuelle
store.add_memory_link("mem_1", "mem_2", weight=1.0, link_type="cooccurrence")

# Automatique (détection de co-occurrences)
engine = store.memory_rank_engine
engine.detect_cooccurrence_links(lookback_days=7)
```

### Mise à jour périodique

```python
# Recalculer les scores (à faire périodiquement)
store.update_memory_ranks()
```

### Utilisation avec décroissance temporelle

```python
from memory_service.memory_rank_engine import MemoryRankEngine

engine = MemoryRankEngine(use_temporal_decay=True, decay_factor=0.01)
ranks = engine.compute_and_update_ranks()
```

## Conclusion

Le système MemoryRank est maintenant pleinement intégré dans le service mémoire de LIA. Il apporte une dimension structurelle à l'importance des souvenirs, au-delà de la simple récence ou similarité.

Les prochaines étapes d'amélioration incluent :
- Optimisation pour grandes échelles (matrice sparse)
- Détection sémantique améliorée (embeddings)
- Classification automatique des niveaux hiérarchiques
- Calcul asynchrone pour meilleure performance


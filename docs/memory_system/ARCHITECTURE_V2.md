# Architecture MemoryRank V2 - Segmentation et Filtrage Sémantique

## Vue d'ensemble

Le système MemoryRank V2 introduit une approche plus sophistiquée de la mémorisation en décomposant les interactions en **unités sémantiques** (phrases) plutôt que de stocker des prompts bruts.

## Principe fondamental

> **Une mémoire intelligente ne stocke pas des tokens. Elle stocke des unités de sens.**

## Architecture en 3 étapes

### Étape 1 : Segmentation en phrases

**Objectif :** Décomposer le prompt/interaction en phrases sémantiques cohérentes.

**Méthode :**
- Détection des limites de phrases (ponctuation, structure)
- Nettoyage et normalisation
- Filtrage des phrases trop courtes ou non informatives

**Exemple :**
```
Prompt: "Je préfère Python à Java. J'aime travailler sur des projets d'IA. Mon objectif est de créer un système autonome."

Phrases extraites:
1. "Je préfère Python à Java"
2. "J'aime travailler sur des projets d'IA"
3. "Mon objectif est de créer un système autonome"
```

### Étape 2 : Filtrage sémantique

**Formule d'importance :**

```
I = α·nouveauté + β·lien RL + γ·centralité
```

où :
- **α** : Poids de la nouveauté (défaut: 0.4)
- **β** : Poids du lien RL (défaut: 0.3)
- **γ** : Poids de la centralité MemoryRank (défaut: 0.3)

**Composantes :**

1. **Nouveauté** : Mesure si la phrase apporte de nouvelles informations
   - Comparaison avec les souvenirs existants (similarité sémantique)
   - Score élevé si la phrase est unique/nouvelle
   - Score faible si redondante avec des souvenirs existants

2. **Lien RL** : Utilité pour l'apprentissage par renforcement
   - Récompenses associées à des phrases similaires
   - Fréquence d'utilisation dans des contextes réussis
   - Score basé sur l'historique RL

3. **Centralité MemoryRank** : Importance structurelle dans le graphe
   - Score MemoryRank calculé sur le graphe de phrases
   - Phrases connectées à beaucoup d'autres phrases importantes
   - Score calculé dynamiquement

**Seuil de stockage :**

```
Si I > θ alors stocker la phrase
```

où **θ** est un seuil configurable (défaut: 0.5)

### Étape 3 : Création du graphe MemoryRank entre phrases

**Types de liens :**

1. **Co-occurrence** : Phrases mentionnées ensemble dans une même interaction
   - Poids basé sur la fréquence de co-occurrence
   - Détection automatique lors du traitement des interactions

2. **Dépendance causale** : Relations causales entre phrases
   - Détection via patterns linguistiques ("parce que", "donc", "si...alors")
   - Analyse de la structure logique

3. **Similarité embedding** : Similarité sémantique calculée via embeddings
   - Utilisation d'un modèle d'embedding (ex: sentence-transformers)
   - Lien créé si similarité > seuil (défaut: 0.7)

**Calcul MemoryRank :**

Une fois les liens créés, le système calcule les scores MemoryRank pour chaque phrase mémorisée, permettant de :
- Identifier les phrases centrales
- Prioriser la récupération des phrases importantes
- Maintenir une hiérarchie sémantique

## Flux de traitement

```
Interaction (prompt + response)
    │
    ├─→ [Segmentation] → Liste de phrases
    │
    ├─→ [Filtrage sémantique] → Pour chaque phrase :
    │       │
    │       ├─→ Calcul nouveauté (vs souvenirs existants)
    │       ├─→ Calcul lien RL (historique)
    │       ├─→ Calcul centralité (MemoryRank actuel)
    │       │
    │       └─→ Score I = α·nouveauté + β·lien RL + γ·centralité
    │
    ├─→ [Décision] → Si I > θ : stocker la phrase
    │
    └─→ [Création liens] → Pour chaque phrase stockée :
            │
            ├─→ Détecter co-occurrences
            ├─→ Détecter dépendances causales
            └─→ Calculer similarités embeddings
                    │
                    └─→ Créer liens dans graphe MemoryRank
```

## Avantages par rapport à V1

### V1 (Stockage brut)
- ❌ Stocke des prompts entiers
- ❌ Pas de filtrage intelligent
- ❌ Redondance importante
- ❌ Explosion mémoire

### V2 (Segmentation + Filtrage)
- ✅ Stocke des unités sémantiques (phrases)
- ✅ Filtrage intelligent basé sur importance
- ✅ Réduction de la redondance
- ✅ Mémoire optimisée et structurée
- ✅ Graphe de concepts au lieu de graphe de prompts

## Intégration avec MemoryRank V1

Le système V2 s'appuie sur MemoryRank V1 :

1. **Centralité MemoryRank** : Utilise le moteur MemoryRank existant pour calculer la centralité
2. **Graphe de liens** : Réutilise `MemoryLinkModel` pour stocker les liens entre phrases
3. **Scores hybrides** : Étend le système de scores hybrides existant

## Composants à implémenter

### 1. `PhraseSegmenter`
- Segmentation en phrases
- Nettoyage et normalisation
- Filtrage des phrases non informatives

### 2. `SemanticFilter`
- Calcul de la nouveauté (similarité avec souvenirs existants)
- Calcul du lien RL (historique des récompenses)
- Calcul de la centralité (MemoryRank)
- Score d'importance combiné

### 3. `PhraseMemoryStore`
- Stockage des phrases comme souvenirs
- Gestion des liens entre phrases
- Intégration avec MemoryRank

### 4. `EmbeddingSimilarity`
- Calcul de similarité sémantique via embeddings
- Détection automatique de liens de similarité

## Exemple d'utilisation

```python
from memory_service.phrase_memory import PhraseMemoryProcessor

processor = PhraseMemoryProcessor(
    alpha=0.4,  # Poids nouveauté
    beta=0.3,   # Poids RL
    gamma=0.3,  # Poids centralité
    threshold=0.5  # Seuil de stockage
)

# Traiter une interaction
interaction = {
    "prompt": "Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
    "response": "Python est effectivement un excellent choix pour l'IA.",
    "session_id": "session_123"
}

# Traitement automatique
phrases_stored = await processor.process_interaction(interaction)

# Résultat : Seules les phrases importantes sont stockées
# avec leurs liens MemoryRank créés automatiquement
```

## Métriques et performance

### Réduction mémoire
- **V1** : Stocke ~100% des interactions importantes
- **V2** : Stocke ~20-40% des phrases (celles qui passent le filtre)

### Qualité
- **V1** : Informations redondantes et bruit
- **V2** : Informations structurées et pertinentes

### Récupération
- **V1** : Récupère des prompts entiers
- **V2** : Récupère des phrases ciblées et leurs connexions

## Prochaines étapes

1. ✅ Architecture définie
2. ⏳ Implémentation de `PhraseSegmenter`
3. ⏳ Implémentation de `SemanticFilter`
4. ⏳ Intégration avec MemoryRank V1
5. ⏳ Tests et validation
6. ⏳ Documentation utilisateur


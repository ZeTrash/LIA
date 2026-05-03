# Améliorations futures pour MemoryRank V2

Ce document liste les améliorations possibles pour le système MemoryRank V2, organisées par priorité et complexité.

## 🔴 Priorité Haute - Court terme

### 1. Support d'embeddings pour la similarité sémantique

**Problème actuel :**
- La similarité utilise uniquement des mots communs (Jaccard)
- Ne capture pas les relations sémantiques (ex: "voiture" vs "automobile")
- Peut manquer des redondances avec formulations différentes

**Solution proposée :**
- Intégrer `sentence-transformers` pour générer des embeddings
- Utiliser des modèles pré-entraînés (ex: `all-MiniLM-L6-v2`)
- Calculer la similarité cosinus entre embeddings

**Implémentation :**
```python
# Dans semantic_filter.py
try:
    from sentence_transformers import SentenceTransformer
    _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    USE_EMBEDDINGS = True
except ImportError:
    USE_EMBEDDINGS = False

def _text_similarity_with_embeddings(self, text1: str, text2: str) -> float:
    embeddings = _embedding_model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return (similarity + 1) / 2  # Normaliser entre 0 et 1
```

**Avantages :**
- Meilleure détection de redondance sémantique
- Capture les synonymes et paraphrases
- Plus précis pour le calcul de nouveauté

**Complexité :** Moyenne
**Temps estimé :** 2-3 heures

---

### 2. Cache des embeddings

**Problème actuel :**
- Si embeddings implémentés, recalculer à chaque fois est coûteux
- Les mêmes phrases sont comparées plusieurs fois

**Solution proposée :**
- Cache en mémoire (dict) pour les embeddings calculés
- Persister dans la base de données (table `phrase_embeddings`)
- Invalidation intelligente du cache

**Implémentation :**
```python
class EmbeddingCache:
    def __init__(self, db_path):
        self.memory_cache = {}
        self.db = Database(db_path)
    
    def get_embedding(self, text: str) -> np.ndarray:
        # Vérifier cache mémoire
        if text in self.memory_cache:
            return self.memory_cache[text]
        
        # Vérifier base de données
        embedding = self._load_from_db(text)
        if embedding is not None:
            self.memory_cache[text] = embedding
            return embedding
        
        # Calculer et stocker
        embedding = self._compute_embedding(text)
        self._save_to_db(text, embedding)
        self.memory_cache[text] = embedding
        return embedding
```

**Avantages :**
- Performance améliorée (évite recalculs)
- Réduction de l'utilisation CPU/GPU
- Scalabilité pour grandes bases de données

**Complexité :** Moyenne
**Temps estimé :** 2-3 heures

---

### 3. Amélioration de la détection de dépendances causales

**Problème actuel :**
- Patterns regex basiques
- Ne capture pas toutes les relations causales
- Peut créer des faux positifs

**Solution proposée :**
- Utiliser des modèles NLP pour la détection de relations
- Patterns plus sophistiqués avec contexte
- Apprentissage des patterns depuis les données

**Implémentation :**
```python
# Patterns améliorés avec contexte
causal_patterns_advanced = [
    # Patterns avec contexte avant/après
    (r'(.+?)\s+(?:parce que|car|étant donné que)\s+(.+?)(?:\.|,|$)', 'because'),
    # Patterns conditionnels
    (r'(.+?)\s+(?:si|quand|lorsque)\s+(.+?)\s+(?:alors|donc|par conséquent)\s+(.+)', 'if_then'),
    # Patterns de conséquence
    (r'(.+?)\s+(?:entraîne|provoque|cause|conduit à)\s+(.+)', 'causes'),
]
```

**Avantages :**
- Meilleure détection des relations causales
- Liens MemoryRank plus pertinents
- Graphe de mémoire plus structuré

**Complexité :** Moyenne
**Temps estimé :** 3-4 heures

---

## 🟡 Priorité Moyenne - Moyen terme

### 4. Persistance de l'historique RL

**Problème actuel :**
- L'historique RL n'est pas persisté
- Perdu à chaque redémarrage
- Ne peut pas apprendre de l'historique long terme

**Solution proposée :**
- Table `rl_history` dans la base de données
- Stocker : phrase, reward, timestamp, contexte
- Requêtes efficaces pour récupérer l'historique

**Implémentation :**
```python
# Nouveau modèle
class RLHistoryModel(Base):
    __tablename__ = 'rl_history'
    
    id = Column(String, primary_key=True)
    phrase = Column(Text, nullable=False)
    reward = Column(Float, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    context = Column(JSON)  # Contexte additionnel
    memory_id = Column(String, ForeignKey('souvenirs.id'))
```

**Avantages :**
- Apprentissage continu sur plusieurs sessions
- Meilleur calcul du score RL
- Historique consultable pour analyse

**Complexité :** Faible-Moyenne
**Temps estimé :** 2-3 heures

---

### 5. Ajustement automatique des poids (α, β, γ)

**Problème actuel :**
- Poids fixes (α=0.4, β=0.3, γ=0.3)
- Pas d'adaptation selon le contexte
- Nécessite réglage manuel

**Solution proposée :**
- Apprentissage automatique des poids optimaux
- A/B testing pour trouver les meilleurs poids
- Adaptation dynamique selon le type de contenu

**Implémentation :**
```python
class AdaptiveWeightOptimizer:
    def __init__(self):
        self.weight_history = []
        self.performance_metrics = []
    
    def optimize_weights(self, training_data):
        # Essayer différentes combinaisons de poids
        best_weights = None
        best_score = 0.0
        
        for alpha in [0.3, 0.4, 0.5]:
            for beta in [0.2, 0.3, 0.4]:
                gamma = 1.0 - alpha - beta
                score = self._evaluate_weights(alpha, beta, gamma, training_data)
                if score > best_score:
                    best_score = score
                    best_weights = (alpha, beta, gamma)
        
        return best_weights
```

**Avantages :**
- Optimisation automatique
- Meilleure performance sans réglage manuel
- Adaptation au contexte spécifique

**Complexité :** Élevée
**Temps estimé :** 1-2 jours

---

### 6. Classification automatique des niveaux hiérarchiques

**Problème actuel :**
- Classification manuelle des catégories (fact, preference, etc.)
- Pas de hiérarchie automatique (event, episode, concept, objective)

**Solution proposée :**
- Modèle de classification automatique
- Détection des niveaux hiérarchiques depuis le contenu
- Intégration avec la hiérarchie fractale

**Implémentation :**
```python
class HierarchicalClassifier:
    def classify_level(self, phrase: str) -> str:
        # Analyser la phrase pour déterminer le niveau
        if self._is_objective(phrase):
            return "objective"
        elif self._is_concept(phrase):
            return "concept"
        elif self._is_episode(phrase):
            return "episode"
        else:
            return "event"
    
    def _is_objective(self, phrase: str) -> bool:
        objective_keywords = ["objectif", "but", "vise", "cherche à"]
        return any(kw in phrase.lower() for kw in objective_keywords)
```

**Avantages :**
- Organisation automatique de la mémoire
- Hiérarchie fractale fonctionnelle
- Meilleure structuration des connaissances

**Complexité :** Moyenne-Élevée
**Temps estimé :** 4-6 heures

---

## 🟢 Priorité Basse - Long terme

### 7. Visualisation du graphe de mémoire

**Problème actuel :**
- Pas de visualisation du graphe MemoryRank
- Difficile de comprendre la structure
- Pas d'outil de débogage visuel

**Solution proposée :**
- Interface web avec visualisation interactive
- Utiliser `networkx` + `plotly` ou `d3.js`
- Filtres et recherche dans le graphe

**Implémentation :**
```python
# Script de visualisation
import networkx as nx
import plotly.graph_objects as go

def visualize_memory_graph(memory_store):
    G = nx.DiGraph()
    # Construire le graphe depuis les liens
    # Visualiser avec plotly
    # Interface web Flask/FastAPI
```

**Avantages :**
- Compréhension visuelle du système
- Débogage facilité
- Analyse de la structure de mémoire

**Complexité :** Élevée
**Temps estimé :** 2-3 jours

---

### 8. Optimisation pour grandes échelles

**Problème actuel :**
- Calcul MemoryRank peut être lent avec beaucoup de souvenirs
- Matrice dense pour PageRank
- Pas d'optimisation pour grandes bases

**Solution proposée :**
- Matrices creuses (sparse matrices)
- Calcul incrémental des scores
- Indexation pour recherches rapides

**Implémentation :**
```python
from scipy.sparse import csr_matrix

def compute_ranks_sparse(memory_graph):
    # Utiliser matrices creuses
    adjacency_matrix = csr_matrix(...)
    # Calcul optimisé avec scipy
```

**Avantages :**
- Performance améliorée
- Scalabilité pour grandes bases
- Utilisation mémoire réduite

**Complexité :** Élevée
**Temps estimé :** 1-2 jours

---

### 9. Intégration avec systèmes RL externes

**Problème actuel :**
- Score RL basique (valeur par défaut)
- Pas d'intégration avec systèmes RL réels

**Solution proposée :**
- API pour recevoir des rewards externes
- Intégration avec frameworks RL (Ray RLlib, Stable-Baselines)
- Feedback loop avec l'agent RL

**Implémentation :**
```python
class ExternalRLIntegration:
    def receive_reward(self, phrase: str, reward: float, context: dict):
        # Enregistrer la récompense
        # Mettre à jour les scores RL
        # Recalculer les importances
```

**Avantages :**
- Intégration avec systèmes RL réels
- Apprentissage basé sur récompenses réelles
- Meilleure adaptation comportementale

**Complexité :** Élevée
**Temps estimé :** 2-3 jours

---

## 📊 Résumé des priorités

| Amélioration | Priorité | Complexité | Temps | Impact |
|--------------|----------|------------|-------|--------|
| Embeddings | 🔴 Haute | Moyenne | 2-3h | Élevé |
| Cache embeddings | 🔴 Haute | Moyenne | 2-3h | Moyen |
| Dépendances causales | 🔴 Haute | Moyenne | 3-4h | Moyen |
| Historique RL | 🟡 Moyenne | Faible-Moyenne | 2-3h | Moyen |
| Poids adaptatifs | 🟡 Moyenne | Élevée | 1-2j | Élevé |
| Classification hiérarchique | 🟡 Moyenne | Moyenne-Élevée | 4-6h | Moyen |
| Visualisation | 🟢 Basse | Élevée | 2-3j | Faible |
| Optimisation grande échelle | 🟢 Basse | Élevée | 1-2j | Moyen |
| Intégration RL externe | 🟢 Basse | Élevée | 2-3j | Faible |

## 🎯 Recommandations

**Pour une amélioration rapide :**
1. Support d'embeddings (impact élevé, temps raisonnable)
2. Cache des embeddings (performance immédiate)
3. Persistance historique RL (apprentissage continu)

**Pour une amélioration à long terme :**
1. Ajustement automatique des poids (optimisation continue)
2. Classification hiérarchique automatique (organisation)
3. Visualisation (compréhension et débogage)

## 📝 Notes

- Les améliorations peuvent être implémentées progressivement
- Chaque amélioration est indépendante (peut être ajoutée séparément)
- Tests requis après chaque amélioration
- Documentation à mettre à jour avec chaque ajout


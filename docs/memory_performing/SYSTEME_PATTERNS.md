# Système de Patterns pour la Planification Cognitive

**Date** : 2024-12-19  
**Statut** : 📋 En conception - Version de départ

> **V2** : Voir [SYSTEME_PATTERNS_V2.md](./SYSTEME_PATTERNS_V2.md) pour le système étendu avec thèmes (`theme_pattern`).

---

## Vue d'ensemble

Le système de patterns permet à LIA d'apprendre des séquences d'actions optimales pour traiter différents types de requêtes utilisateur. L'objectif est d'améliorer progressivement la qualité des décisions en s'appuyant sur les retours de Gemini (source externe de connaissances).

---

## Architecture du Système

### 1. Collecte des Patterns

Après chaque génération de réponse finale à l'utilisateur, le système :

1. **Collecte les informations** :
   - La requête utilisateur originale
   - La suite d'actions choisie par l'agent (ex: `B1, B2, G1, G4`)
   - La liste complète des actions disponibles au moment de chaque choix

2. **Interroge Gemini** pour obtenir la suite optimale :
   ```
   Pour traiter la requête de l'utilisateur "{requête utilisateur}" 
   j'ai choisi cette suite d'actions {suite d'actions, ex: B1, B2, G1, G4} 
   parmi cette liste d'actions disponibles.
   
   Quelle aurait été la suite de choix optimale pour cette requête ?
   Répondre uniquement en format suite avec {Xy, Xy, Xy, ...}
   ```

3. **Valide le format** :
   - Si le format n'est pas valide (pas de format `{Xy, Xy, ...}`), relancer Gemini jusqu'à obtenir un format correct
   - Maximum de tentatives : 3

### 2. Stockage des Patterns

#### Structure de données : Tableau de Patterns

Chaque pattern est stocké dans un tableau avec :
- **Clé** : Identifiant de l'action (ex: `B1`, `B2`, `G1`, `G2`, etc.)
- **Valeur** : Poids associé à cette action dans le contexte donné
- **Contrainte** : La somme des poids d'une suite d'actions = 1.0

#### Système de poids

Les poids dépendent de l'ordre d'apparition dans la suite recommandée par Gemini :
- **Première action** : Poids le plus élevé
- **Actions suivantes** : Poids décroissants
- **Formule** : `poids(action_i) = (n - i + 1) / somme(1..n)` où `n` est le nombre d'actions

**Exemple** :
- Suite recommandée : `G1, G2, G4`
- Poids : `G1 = 0.5`, `G2 = 0.33`, `G4 = 0.17` (somme = 1.0)

### 3. Utilisation des Patterns

#### Approche 1 : Recommandation directe (simple)

Lorsqu'un menu arrive, le système :
1. Identifie le contexte actuel (menu de base, menu général, etc.)
2. Consulte le pattern avec le poids le plus élevé pour ce contexte
3. Ajoute une section dans le prompt du menu :
   ```
   === RECOMMANDATION ===
   Le choix recommandé est 1, mais vous pouvez choisir une autre option.
   ```

**Avantages** :
- Simple à implémenter
- Recommandation claire pour l'agent

**Inconvénients** :
- Ne prend pas en compte la séquence complète
- Peut recommander des actions qui ne sont pas optimales dans le contexte global

#### Approche 2 : Matrice de transitions (recommandée)

Créer une **matrice de transitions** qui indique :
- Pour un choix donné (ex: `G1`), quel est le choix optimal suivant (ex: `G2`)
- Pour le premier menu (pas encore de choix), quel est le choix optimal initial (ex: `G1`)

**Structure** :
```python
transition_matrix = {
    "base": {
        "initial": "G1",  # Choix optimal au premier menu
        "B1": "G1",       # Après B1, choix optimal suivant
        "B2": "G2",       # Après B2, choix optimal suivant
        # ...
    },
    "general": {
        "G1": "G4",       # Après G1, choix optimal suivant
        "G2": "G5",       # Après G2, choix optimal suivant
        # ...
    }
}
```

**Utilisation dans le prompt** :
```
=== RECOMMANDATION ===
Étant donné vos choix précédents, le choix recommandé est 1, 
mais vous pouvez choisir une autre option.
```

**Avantages** :
- Prend en compte la séquence complète
- Plus flexible et contextuel
- Permet d'apprendre des patterns complexes

**Inconvénients** :
- Plus complexe à implémenter
- Nécessite plus de données pour être efficace

---

## Implémentation Proposée

### Phase 1 : Collecte et Stockage

1. **Après chaque réponse finale** :
   - Collecter la suite d'actions exécutée
   - Envoyer la requête à Gemini
   - Parser la réponse de Gemini (format `{Xy, Xy, ...}`)
   - Calculer les poids selon l'ordre
   - Stocker dans la mémoire (table `patterns`)

> **Ordre de phases (mis à jour)**
>
> Avant de brancher Gemini, on commence par :
> - créer la table `patterns`,
> - seed des patterns fictifs,
> - vérifier l'inclusion d'une recommandation dans le prompt du menu.
>
> Une fois que c'est stable, on implémente la collecte + Gemini.

2. **Structure de stockage** :
   ```python
   {
       "user_request_pattern": "bonjour",  # Pattern de la requête (normalisé)
       "actions_sequence": ["B1", "G1", "G4"],
       "weights": {
           "B1": 0.5,
           "G1": 0.33,
           "G4": 0.17
       },
       "gemini_recommendation": ["B1", "G1", "G4"],  # Suite recommandée
       "created_at": "2024-12-19T10:00:00"
   }
   ```

### Phase 2 : Utilisation dans les Menus

1. **Lors de la construction du menu** :
   - Identifier le contexte (menu de base, menu général)
   - Consulter les patterns pertinents
   - Calculer la recommandation (approche 1 ou 2)
   - Ajouter la section `=== RECOMMANDATION ===` dans le prompt

2. **Intégration dans `_decision_prompt`** :
   ```python
   def _decision_prompt(..., pattern_recommendation: Optional[int] = None):
       # ... code existant ...
       
       if pattern_recommendation:
           lines.append("=== RECOMMANDATION ===")
           lines.append(f"Le choix recommandé est {pattern_recommendation}, "
                       f"mais vous pouvez choisir une autre option.")
           lines.append("")
   ```

---

## Réflexions et Recommandations

### Points Positifs

1. **Apprentissage progressif** : Le système s'améliore avec le temps
2. **Source externe fiable** : Gemini peut fournir des insights valides
3. **Non-intrusif** : La recommandation est suggérée, pas imposée
4. **Flexible** : L'agent peut toujours choisir une autre option

### Points d'Attention

1. **Qualité des patterns Gemini** :
   - Gemini peut recommander des suites qui ne sont pas adaptées au contexte spécifique de LIA
   - Il faut valider que les recommandations sont cohérentes avec les capacités réelles de LIA

2. **Surcharge de requêtes Gemini** :
   - Chaque interaction génère une requête Gemini
   - Coût et latence à considérer
   - **Solution** : Limiter aux requêtes importantes ou batch les requêtes

3. **Patterns obsolètes** :
   - Les patterns peuvent devenir obsolètes si le système évolue
   - **Solution** : Système de versioning ou expiration des patterns

4. **Biais dans les patterns** :
   - Si Gemini recommande toujours les mêmes suites, cela peut créer un biais
   - **Solution** : Diversifier les sources de recommandations ou introduire de la variabilité

### Recommandations

1. **Commencer par l'Approche 1** (recommandation simple) :
   - Plus simple à implémenter
   - Permet de valider le concept rapidement
   - Facilite le débogage

2. **Évoluer vers l'Approche 2** (matrice de transitions) :
   - Une fois que l'Approche 1 fonctionne bien
   - Permet une meilleure prise en compte du contexte

3. **Ajouter un système de confiance** :
   - Ne recommander que si la confiance dans le pattern est élevée
   - Permet d'éviter de mauvaises recommandations

4. **Limiter les requêtes Gemini** :
   - Ne pas interroger Gemini pour chaque interaction
   - Utiliser un système de batch ou de seuil (ex: toutes les 10 interactions)

5. **Validation des patterns** :
   - Vérifier que les actions recommandées existent dans le menu actuel
   - Gérer les cas où le menu a changé depuis l'apprentissage du pattern

---

## Prochaines Étapes

1. ✅ Documenter le système (ce document)
2. ✅ Stabiliser la mémoire et les menus (semences fictives, tests d'inclusion dans les prompts)
3. ⏳ Implémenter la collecte des patterns après chaque réponse (une fois mémoire + menus stables)
4. ⏳ Implémenter l'interrogation de Gemini avec validation du format
5. ⏳ Implémenter le stockage des patterns avec poids
6. ⏳ Implémenter la consultation des patterns lors de la construction des menus
7. ⏳ Intégrer la recommandation dans le prompt de décision
8. ⏳ Tester et ajuster le système

---

## Questions Ouvertes

1. **Fréquence des requêtes Gemini** : À quelle fréquence interroger Gemini ?
2. **Gestion des patterns contradictoires** : Que faire si Gemini recommande des suites différentes pour des requêtes similaires ?
3. **Mise à jour des patterns** : Comment mettre à jour les patterns existants avec de nouvelles données ?
4. **Performance** : Comment optimiser la recherche de patterns pertinents dans une base de données croissante ?


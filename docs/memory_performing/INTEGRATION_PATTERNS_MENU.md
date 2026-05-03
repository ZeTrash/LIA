# Intégration Système de Patterns V2 avec Menu Optimal

**Date** : 2025-02-20  
**Statut** : 📋 Documentation  
**Version** : 1.0

---

## Vue d'ensemble

Ce document clarifie l'intégration entre le **système de patterns V2** (utilisant Gemini/Groq) et le **menu optimal** adapté à MemoryRank V2.

## Principe fondamental

> **Le système de patterns V2 détermine AUTOMATIQUEMENT les choix dans le menu optimal en utilisant les patterns classifiés par Gemini/Groq et stockés dans la mémoire. L'agent local n'est plus sollicité pour choisir dans les menus.**

**Mode par défaut** : `LIA_PATTERNS_ONLY=1` (activé par défaut)
- Les patterns sont utilisés directement depuis la mémoire
- Aucune consultation de l'agent local pour les choix de menu
- Fallback sûr si aucun pattern disponible (généralement RESPOND)

## Flux complet intégré

### Étape 1 : Classification du thème (Gemini/Groq)

**Avant la planification cognitive** :

```
Requête utilisateur : "Qui es-tu ?"
    │
    ├─→ [Gemini/Groq] → Classification du thème
    │   Prompt : "Pour cette requête, choisissez un thème parmi {thèmes_disponibles}"
    │   Sortie : theme_pattern = "identité"
    │
    └─→ [PatternLearner] → Récupère les patterns pour ce thème
```

**Code** :
```python
# Dans LLMAdapter ou CognitivePlanner
theme_pattern = await classify_theme_with_gemini(user_request, available_themes)
patterns = pattern_learner.get_patterns_for_theme(theme_pattern)
```

### Étape 2 : Utilisation directe des patterns (pas de choix par l'agent)

**Le système utilise DIRECTEMENT les patterns depuis la mémoire** :

```python
# Dans LLMAdapter._generate_with_planner()
# Mode "patterns-only" : activé par défaut (LIA_PATTERNS_ONLY=1)

# 1. Récupérer le pattern recommandé depuis la mémoire
theme_pattern = execution_results.get("_theme_pattern")
pattern_rec = self.pattern_learner.get_pattern_recommendation(
    menu_context="base",
    prev_step="initial",
    theme_pattern=theme_pattern
)

# 2. Si pattern disponible, utiliser directement l'action recommandée
if pattern_rec:
    recommended_action_code = pattern_rec["recommended_step"]
    # Trouver l'action correspondante dans le menu
    chosen_action = find_action_by_code(menu, recommended_action_code)
    logger.info(f'🗳️  [LLM_ADAPTER] Choix automatique via pattern: "{recommended_action_code}"')
else:
    # Fallback sûr : choisir RESPOND ou première action disponible
    chosen_action = find_respond_action(menu) or menu[0]
    logger.info(f'🗳️  [LLM_ADAPTER] Fallback (pas de pattern): "{chosen_action.type.value}"')

# 3. AUCUNE consultation de l'agent local pour le choix
# Le pattern détermine directement l'action à exécuter
```

### Étape 3 : Exécution automatique

**L'action déterminée par le pattern est exécutée automatiquement** :
- Pas de prompt de décision envoyé à l'agent local
- Pas de choix à faire par l'agent
- L'action recommandée par le pattern est directement exécutée

### Étape 4 : Apprentissage du pattern (Gemini/Groq)

**Après la génération de la réponse finale** :

```
Séquence d'actions exécutée automatiquement : [B3, G1, G5]
    │
    ├─→ [Gemini/Groq] → Apprentissage du pattern optimal
    │   Prompt : "Pour cette requête '{requête}', j'ai exécuté {séquence}.
    │            Quelle aurait été la suite optimale ?"
    │   Format attendu : {{theme_pattern},{B2, G1, G5}}
    │
    └─→ [PatternLearner] → Mise à jour des patterns dans la DB
        - Upsert pattern avec theme_pattern, menu_context, prev_step
        - Calcul des poids selon l'ordre recommandé
        - Les patterns mis à jour seront utilisés pour les prochaines requêtes similaires
```

**Code** :
```python
# Dans LLMAdapter._learn_menu_patterns_with_agent()
executed_sequence = ["B3", "G1", "G5"]
theme_pattern = execution_results.get("_theme_pattern", "no_pattern")

# Appel Gemini/Groq
gemini_response = await gemini_adapter.generate(pattern_learning_prompt)
# Parse : {{theme_pattern},{B2, G1, G5}}
parsed = parse_pattern_response(gemini_response)

# Mise à jour dans la DB
for step in parsed:
    pattern_learner.upsert_pattern(
        theme_pattern=theme_pattern,
        menu_context=step.context,
        prev_step=step.prev,
        recommended_step=step.recommended,
        weights=calculate_weights(step.sequence)
    )
```

## Intégration dans le Menu Optimal

### 1. MenuBuilder enrichi avec Patterns

```python
class MenuBuilder:
    def __init__(self, memory_store, pattern_learner):
        self.memory_store = memory_store
        self.pattern_learner = pattern_learner  # Utilise Gemini/Groq
    
    def build_base_menu(self, user_request, execution_results, session_id):
        # Récupérer le thème classifié
        theme_pattern = execution_results.get("_theme_pattern")
        
        # Construire le menu
        menu = self._build_menu_actions(user_request, execution_results)
        
        # Obtenir recommandation de pattern
        pattern_rec = self.pattern_learner.get_pattern_recommendation(
            menu_context="base",
            prev_step=execution_results.get("_last_step", "initial"),
            theme_pattern=theme_pattern
        )
        
        # Enrichir avec MemoryRank
        menu = self._enrich_with_memory_rank(menu, user_request)
        
        return menu, pattern_rec
```

### 2. Utilisation directe du pattern (pas d'affichage de menu)

**Le pattern détermine directement l'action, pas besoin de prompt de décision** :

```python
# Dans LLMAdapter._generate_with_planner()
# Mode patterns-only (LIA_PATTERNS_ONLY=1 par défaut)

# 1. Récupérer le pattern depuis la mémoire
pattern_rec = self.pattern_learner.get_pattern_recommendation(
    menu_context=menu_context,
    prev_step=prev_step,
    theme_pattern=theme_pattern
)

# 2. Si pattern disponible, utiliser directement
if pattern_rec:
    recommended_code = pattern_rec["recommended_step"]
    chosen_action = find_action_by_code(menu, recommended_code)
    logger.info(f'✅ [PATTERNS] Action choisie automatiquement: {recommended_code}')
else:
    # Fallback : RESPOND ou première action
    chosen_action = find_respond_action(menu) or menu[0]
    logger.info(f'⚠️  [PATTERNS] Fallback (pas de pattern): {chosen_action.type.value}')

# 3. Exécuter directement l'action (pas de prompt de décision)
# L'agent local n'est PAS consulté pour choisir dans le menu
```

### 3. Classification du thème et utilisation automatique des patterns

**Dans `LLMAdapter._generate_with_planner()`** :

```python
async def _generate_with_planner(self, message, session_id):
    # ÉTAPE 1 : Classification du thème (Gemini/Groq)
    theme_pattern = await self._classify_theme_with_gemini(message)
    execution_results["_theme_pattern"] = theme_pattern
    
    # ÉTAPE 2 : Planification cognitive (utilise les patterns du thème)
    plan = await self.cognitive_planner.plan(message, session_id)
    
    # ÉTAPE 3 : Boucle de menus avec utilisation AUTOMATIQUE des patterns
    # Mode patterns-only (LIA_PATTERNS_ONLY=1 par défaut)
    for iteration in range(max_iterations):
        menu = self.cognitive_planner.build_action_menu(...)
        
        # Récupérer pattern depuis la mémoire
        pattern_rec = self.pattern_learner.get_pattern_recommendation(
            menu_context=menu_context,
            prev_step=prev_step,
            theme_pattern=theme_pattern
        )
        
        # Utiliser directement le pattern (pas de consultation de l'agent)
        if pattern_rec:
            chosen_action = find_action_by_code(menu, pattern_rec["recommended_step"])
        else:
            chosen_action = find_respond_action(menu) or menu[0]  # Fallback
        
        # Exécuter l'action directement
        result = await self.action_executor.execute(chosen_action, ...)
        
        if chosen_action.type == ActionType.RESPOND:
            break  # Réponse finale générée
    
    # ÉTAPE 4 : Apprentissage (après réponse finale)
    await self._learn_menu_patterns_with_agent(message, plan)
```

## Enrichissement avec MemoryRank

### Patterns + MemoryRank = Recommandation optimale

Le menu optimal combine :
1. **Patterns appris** (via Gemini/Groq) → Suggère les actions fréquemment efficaces
2. **MemoryRank** → Priorise les informations importantes dans la mémoire

**Exemple** :

```python
# Pattern suggère : B3 (Consulter connaissance de soi)
# MemoryRank suggère : G1 (Identité) car MemoryRank élevé
# → Recommandation combinée : B3 puis G1
```

### Calcul de pertinence combinée

```python
def calculate_action_relevance(action, user_request, memory_context):
    # Score basé sur pattern
    pattern_score = get_pattern_score(action, memory_context.theme_pattern)
    
    # Score basé sur MemoryRank
    memory_rank_score = get_memory_rank_relevance(action, user_request)
    
    # Score basé sur contexte sémantique
    semantic_score = calculate_semantic_relevance(action, user_request)
    
    # Score combiné
    combined_score = (
        0.4 * pattern_score +
        0.3 * memory_rank_score +
        0.3 * semantic_score
    )
    
    return combined_score
```

## Flux complet illustré

```
┌─────────────────────────────────────────────────────────────────┐
│ REQUÊTE UTILISATEUR : "Qui es-tu ?"                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 1 : Classification thème (Gemini/Groq)                  │
│   → theme_pattern = "identité"                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 2 : Récupération patterns pour thème "identité"          │
│   → Pattern recommandé : B3 (menu base)                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 3 : Construction menu avec MemoryRank                    │
│   Menu Base :                                                   │
│   1. B1 [Pertinence: 0.6]                                       │
│   2. B2 [Pertinence: 0.7]                                       │
│   3. B3 [Pertinence: 0.9] ← Pattern recommandé                │
│   4. B5                                                         │
│                                                                 │
│   Recommandation : 3 (B3) basé sur pattern "identité"         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 4 : Utilisation automatique du pattern → B3              │
│   → Pattern déterminé depuis la mémoire                         │
│   → Aucune consultation de l'agent local                        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 5 : Menu général avec MemoryRank                         │
│   → Top identité (MemoryRank élevé) affiché en premier         │
│   → Pattern depuis mémoire suggère G1 (Connaître identité)     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 6 : Utilisation automatique du pattern → G1              │
│   → Pattern déterminé depuis la mémoire                         │
│   → Affichage identité triée par MemoryRank                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 7 : Utilisation automatique du pattern → G5 (Répondre)  │
│   → Pattern déterminé depuis la mémoire                         │
│   → Génération réponse finale                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE 8 : Apprentissage pattern (Gemini/Groq)                  │
│   Séquence exécutée automatiquement : [B3, G1, G5]              │
│   → Gemini suggère : {{identité},{B3, G1, G5}}                 │
│   → Mise à jour patterns dans DB                               │
│   → Patterns utilisés pour les prochaines requêtes similaires  │
└─────────────────────────────────────────────────────────────────┘
```

## Avantages de l'intégration

### 1. Décisions automatiques et rapides
- **Pas de latence** : Aucune consultation de l'agent local pour choisir dans les menus
- **Décisions instantanées** : Les patterns sont utilisés directement depuis la mémoire
- **Performance optimale** : Réduction du nombre d'appels LLM

### 2. Apprentissage progressif
- Les patterns s'améliorent avec chaque interaction
- Gemini/Groq fournit des recommandations optimales lors de l'apprentissage
- Le système apprend les meilleures séquences automatiquement

### 3. Adaptation contextuelle
- Patterns spécifiques par thème (classifiés par Gemini/Groq)
- Recommandations adaptées au contexte de la requête
- Meilleure pertinence grâce à la classification de thème

### 4. Combinaison Patterns + MemoryRank
- Patterns déterminent les actions fréquemment efficaces
- MemoryRank priorise les informations importantes dans les résultats
- Décisions plus précises et pertinentes

### 5. Fiabilité
- Fallback sûr si aucun pattern disponible (généralement RESPOND)
- Patterns appris progressivement et stockés dans la DB
- Système robuste même avec peu de patterns initiaux

## Configuration

### Mode patterns-only (par défaut)

**Variable d'environnement** : `LIA_PATTERNS_ONLY=1` (activé par défaut)

```python
# Dans LLMAdapter
# Mode patterns-only : utilise directement les patterns depuis la mémoire
# Pas de consultation de l'agent local pour choisir dans les menus

# Si LIA_PATTERNS_ONLY=1 (défaut) :
# - Les patterns sont utilisés directement depuis la DB
# - Aucune consultation de l'agent local pour les choix de menu
# - Fallback sûr si aucun pattern disponible

# Si LIA_PATTERNS_ONLY=0 :
# - L'agent local est consulté pour choisir dans les menus (ancien comportement)
# - Les patterns peuvent être affichés comme recommandations
```

### Désactivation du mode patterns-only

Pour revenir au comportement avec choix par l'agent local :

```bash
export LIA_PATTERNS_ONLY=0
# ou
export LIA_PATTERNS_ONLY=false
```

### Si Gemini/Groq n'est pas disponible

- Les patterns existants dans la DB sont utilisés
- Pas de classification de thème (utilise `no_pattern`)
- Pas d'apprentissage nouveau
- Le menu fonctionne toujours avec MemoryRank
- Fallback sûr si aucun pattern disponible

## Rétrocompatibilité

- ✅ Patterns V1 (sans thème) fonctionnent toujours
- ✅ Patterns V2 (avec thème) sont prioritaires si disponibles
- ✅ Fallback automatique si Gemini/Groq indisponible
- ✅ Menu optimal fonctionne avec ou sans patterns

## Prochaines étapes

1. **Implémentation** : Intégrer la classification de thème dans `LLMAdapter`
2. **MenuBuilder** : Utiliser les patterns pour les recommandations
3. **Tests** : Valider l'intégration complète
4. **Documentation** : Mettre à jour les guides utilisateur

## Références

- **Système de Patterns V2** : `SYSTEME_PATTERNS_V2.md`
- **Menu Optimal** : `CONCEPT_MENU_OPTIMAL.md`
- **Architecture Menu** : `ARCHITECTURE_MENU_OPTIMAL.md`


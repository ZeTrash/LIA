# Architecture Technique et Plan d'Implémentation
## Système de Planification Cognitive pour LIA

**Date** : 2024-12-19  
**Version** : 1.0  
**Auteur** : Architecture basée sur `prompt_memory_performing.md`

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture Technique](#architecture-technique)
3. [Composants Principaux](#composants-principaux)
4. [Plan d'Implémentation](#plan-dimplémentation)
5. [Intégration avec l'Existant](#intégration-avec-lexistant)
6. [Garde-fous et Contrôles](#garde-fous-et-contrôles)
7. [Métriques et Évaluation](#métriques-et-évaluation)

---

## Vue d'ensemble

### Changement de Paradigme

**Modèle actuel** :
```
Question utilisateur → Prompt fixe → LLM → Réponse
```

**Nouveau modèle** :
```
Question utilisateur
    ↓
Décision interne (CognitivePlanner)
    ↓
Accès mémoire / outils / identité (selon décision)
    ↓
Construction dynamique du prompt
    ↓
LLM génère réponse
    ↓
Auto-critique + validation
    ↓
Mise à jour mémoire + patterns
```

### Objectifs Principaux

1. **Planification d'actions internes** : LIA choisit elle-même quelles informations consulter
2. **Mémoire auto-gérée** : LIA décide quoi mémoriser (réduction du bruit)
3. **Apprentissage de patterns** : LIA apprend quelles suites d'actions sont efficaces
4. **Auto-vérification** : Validation avant envoi de la réponse

---

## Architecture Technique

### 1. Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Utilisateur                    │
│              (Web, CLI, API, etc.)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              LLMAdapter (Noyau Primaire)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         CognitivePlanner (NOUVEAU)                    │   │
│  │  - Analyse la requête                                │   │
│  │  - Décide quelles actions prendre                    │   │
│  │  - Construit le plan d'exécution                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                       │                                       │
│                       ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         ActionExecutor (NOUVEAU)                      │   │
│  │  - Exécute les actions décidées                      │   │
│  │  - Accède à la mémoire                                │   │
│  │  - Consulte l'identité                                │   │
│  │  - Utilise les outils externes                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                       │                                       │
│                       ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         PromptBuilder (MODIFIÉ)                      │   │
│  │  - Construit le prompt dynamiquement                │   │
│  │  - Utilise uniquement les informations nécessaires  │   │
│  └──────────────────────────────────────────────────────┘   │
│                       │                                       │
│                       ▼                                       │
│              Génération LLM                                   │
│                       │                                       │
│                       ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SelfVerifier (NOUVEAU)                       │   │
│  │  - Vérifie la pertinence                             │   │
│  │  - Vérifie l'utilisation mémoire                     │   │
│  │  - Valide la réponse                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              PatternLearner (NOUVEAU)                         │
│  - Enregistre les suites d'actions                           │
│  - Évalue l'efficacité                                       │
│  - Met à jour les patterns préférés                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              MemoryAdapter (EXISTANT)                         │
│  - Stockage et récupération                                  │
│  - Gestion mémoire auto (NOUVEAU)                           │
└─────────────────────────────────────────────────────────────┘
```

### 2. Flux de Données Détaillé

```
0. Requête utilisateur arrive (requête "de base")
   ↓
1. Démarrage d'une boucle cognitive (bornée) : 1 requête utilisateur → N itérations internes

   Remarque clé :
   - Le "Système de Planification Cognitive" peut être statique dans sa structure (ex: arbre de décision),
     mais son exécution est itérative : l'agent peut enchaîner plusieurs sous-requêtes internes avant
     de répondre à la requête de base.
   - Concrètement, une requête utilisateur peut déclencher plusieurs appels internes (LLM + outils + mémoire),
     jusqu'à atteindre un état "RESPOND" validé.

2. Pour chaque itération i (i = 1..max_iterations) :
   2.1. CognitivePlanner.plan() analyse la requête de base + l'état courant
        ├─ Consulte PatternLearner pour patterns préférés
        ├─ Analyse la complexité et les besoins (mémoire / identité / outils)
        └─ Génère un plan d'actions (arbre de décision, profondeur bornée)
        ↓
   2.2. ActionExecutor.execute_plan() exécute le plan
        ├─ Action: CONSULT_MEMORY → MemoryAdapter.get_context()
        ├─ Action: CONSULT_IDENTITY → MemoryAdapter.get_traits()
        ├─ Action: CONSULT_PATTERNS → PatternLearner.get_preferred()
        ├─ Action: QUERY_EXTERNAL → GeminiAdapter.query()
        └─ Action: RESPOND → prépare la génération de réponse
        ↓
   2.3. PromptBuilder.build_dynamic_prompt() construit le prompt de l'itération
        ├─ Utilise uniquement les informations récupérées à cette itération
        ├─ Structure optimisée selon le contexte
        └─ Évite les redondances
        ↓
   2.4. LLM produit soit :
        ├─ une décision / étape intermédiaire (si le design l'exige), et/ou
        └─ une réponse candidate pour la requête de base
        ↓
   2.5. SelfVerifier.verify() valide le résultat de l'itération
        ├─ Vérifie pertinence avec la question de base
        ├─ Vérifie utilisation mémoire (pas de souvenirs inutiles)
        ├─ Vérifie cohérence avec l'identité
        └─ Décide : "accepter" ou "re-planifier"

3. Si validation OK → Envoi de la réponse finale (sortie de boucle)
   Si validation KO → itération suivante (plan ajusté) ou fallback borné
   ↓
4. PatternLearner.record_execution() enregistre l'exécution
   ├─ Suite d'actions utilisée (sur N itérations)
   ├─ Résultat (succès/échec)
   ├─ Métriques (temps, tokens, qualité)
   └─ Met à jour les patterns préférés
   ↓
5. MemoryManager.decide_what_to_store() décide quoi mémoriser
   ├─ Analyse l'interaction complète (incluant itérations internes pertinentes)
   ├─ Identifie les éléments importants
   └─ Stocke uniquement ce qui est pertinent
```

---

## Composants Principaux

### 1. CognitivePlanner

**Fichier** : `core/cognitive_planner.py`

**Responsabilités** :
- Analyser la requête utilisateur
- Décider quelles actions prendre (arbre de décision)
- Consulter les patterns préférés
- Générer un plan d'exécution

**Interface** :
```python
class CognitivePlanner:
    def __init__(self, memory_adapter, pattern_learner, config):
        """
        Initialise le planificateur cognitif.
        
        Args:
            memory_adapter: Adaptateur mémoire
            pattern_learner: Apprenant de patterns
            config: Configuration (profondeur max, budget réflexion, etc.)
        """
    
    async def plan(
        self, 
        user_message: str, 
        session_id: str
    ) -> ActionPlan:
        """
        Génère un plan d'actions pour répondre à la requête.
        
        Returns:
            ActionPlan: Plan d'exécution avec actions ordonnées
        """
    
    def _analyze_request(self, message: str) -> RequestAnalysis:
        """
        Analyse la requête pour déterminer sa complexité et besoins.
        """
    
    def _build_decision_tree(self, analysis: RequestAnalysis) -> DecisionNode:
        """
        Construit l'arbre de décision hiérarchique.
        """
```

**Arbre de Décision Hiérarchique** :

```
Niveau 0 (Base)
├─ 1. Consulter patterns préférés
├─ 2. Consulter mémoire et identité
└─ 3. Répondre directement

Niveau 1 (Si choix 2)
├─ 1. Connaître mon identité
├─ 2. Connaître mes traits
├─ 3. Connaître environnement/capacités
├─ 4. Consulter ma mémoire
└─ 5. Revenir au niveau 0

Niveau 2 (Si choix 4)
├─ 1. Consulter n dernières interactions
├─ 2. Consulter n derniers souvenirs
├─ 3. Consulter interaction spécifique
├─ 4. Consulter souvenir spécifique
├─ 5. Explorer la mémoire (recherche)
└─ 6. Revenir au niveau 1

... (profondeur configurable)
```

**Structure ActionPlan** :
```python
@dataclass
class ActionPlan:
    """Plan d'exécution avec actions ordonnées."""
    actions: List[Action]
    estimated_cost: float  # Coût estimé (tokens, temps)
    confidence: float  # Confiance dans le plan
    fallback_plan: Optional['ActionPlan'] = None

@dataclass
class Action:
    """Action à exécuter."""
    type: ActionType  # CONSULT_MEMORY, CONSULT_IDENTITY, etc.
    parameters: Dict[str, Any]  # Paramètres spécifiques
    priority: int  # Ordre d'exécution
    required: bool  # Action obligatoire ou optionnelle
```

### 2. ActionExecutor

**Fichier** : `core/action_executor.py`

**Responsabilités** :
- Exécuter les actions du plan
- Gérer les dépendances entre actions
- Récupérer les résultats
- Gérer les erreurs et fallbacks

**Interface** :
```python
class ActionExecutor:
    def __init__(self, memory_adapter, gemini_adapter, pattern_learner):
        """
        Initialise l'exécuteur d'actions.
        """
    
    async def execute_plan(
        self, 
        plan: ActionPlan, 
        session_id: str
    ) -> ExecutionResult:
        """
        Exécute un plan d'actions.
        
        Returns:
            ExecutionResult: Résultats de toutes les actions
        """
    
    async def execute_action(
        self, 
        action: Action, 
        context: Dict[str, Any]
    ) -> Any:
        """
        Exécute une action spécifique.
        """
```

**Types d'Actions** :
```python
class ActionType(Enum):
    CONSULT_PATTERNS = "consult_patterns"
    CONSULT_MEMORY = "consult_memory"
    CONSULT_IDENTITY = "consult_identity"
    CONSULT_TRAITS = "consult_traits"
    CONSULT_ENVIRONMENT = "consult_environment"
    CONSULT_INTERACTIONS = "consult_interactions"
    CONSULT_MEMORIES = "consult_memories"
    SEARCH_MEMORY = "search_memory"
    QUERY_EXTERNAL = "query_external"  # Gemini
    RESPOND = "respond"
```

### 3. PromptBuilder (Modifié)

**Fichier** : `core/prompt_builder.py` (nouveau, extrait de `llm_adapter.py`)

**Responsabilités** :
- Construire le prompt dynamiquement
- Utiliser uniquement les informations récupérées
- Optimiser la structure selon le contexte
- Éviter les redondances

**Interface** :
```python
class PromptBuilder:
    def __init__(self, config):
        """
        Initialise le constructeur de prompts.
        """
    
    def build_dynamic_prompt(
        self,
        user_message: str,
        execution_result: ExecutionResult,
        context: Dict[str, Any]
    ) -> str:
        """
        Construit un prompt optimisé avec uniquement les informations nécessaires.
        """
    
    def _optimize_structure(
        self, 
        sections: List[PromptSection]
    ) -> str:
        """
        Optimise la structure du prompt pour éviter redondances.
        """
```

### 4. SelfVerifier

**Fichier** : `core/self_verifier.py`

**Responsabilités** :
- Vérifier la pertinence de la réponse
- Vérifier l'utilisation mémoire
- Valider la cohérence avec l'identité
- Calculer un score de qualité

**Interface** :
```python
class SelfVerifier:
    def __init__(self, memory_adapter, config):
        """
        Initialise le vérificateur auto.
        """
    
    async def verify(
        self,
        user_message: str,
        response: str,
        execution_result: ExecutionResult,
        session_id: str
    ) -> VerificationResult:
        """
        Vérifie la réponse avant envoi.
        
        Returns:
            VerificationResult: Résultat de la vérification
        """
    
    def _check_relevance(
        self, 
        question: str, 
        answer: str
    ) -> float:
        """
        Vérifie si la réponse répond à la question.
        """
    
    def _check_memory_usage(
        self, 
        response: str, 
        memories_used: List[str]
    ) -> float:
        """
        Vérifie si les souvenirs utilisés étaient pertinents.
        """
    
    def _check_identity_coherence(
        self, 
        response: str, 
        identity: Dict[str, Any]
    ) -> float:
        """
        Vérifie la cohérence avec l'identité de LIA.
        """
```

**Structure VerificationResult** :
```python
@dataclass
class VerificationResult:
    """Résultat de la vérification."""
    is_valid: bool
    relevance_score: float  # 0.0 - 1.0
    memory_usage_score: float  # 0.0 - 1.0
    identity_coherence_score: float  # 0.0 - 1.0
    overall_score: float  # Score global
    issues: List[str]  # Liste des problèmes détectés
    suggestions: List[str]  # Suggestions d'amélioration
```

### 5. PatternLearner

**Fichier** : `core/pattern_learner.py`

**Responsabilités** :
- Enregistrer les suites d'actions exécutées
- Évaluer l'efficacité des patterns
- Maintenir une base de patterns préférés
- Apprendre quelles suites sont optimales

**Interface** :
```python
class PatternLearner:
    def __init__(self, memory_adapter, config):
        """
        Initialise l'apprenant de patterns.
        """
    
    def get_preferred_patterns(
        self, 
        request_type: str, 
        context: Dict[str, Any]
    ) -> List[Pattern]:
        """
        Retourne les patterns préférés pour un type de requête.
        """
    
    def record_execution(
        self,
        plan: ActionPlan,
        execution_result: ExecutionResult,
        verification_result: VerificationResult,
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Enregistre l'exécution d'un plan pour apprentissage.
        """
    
    def _evaluate_pattern_efficiency(
        self, 
        pattern: Pattern
    ) -> float:
        """
        Évalue l'efficacacité d'un pattern.
        """
    
    def _update_preferred_patterns(self) -> None:
        """
        Met à jour la liste des patterns préférés.
        """
```

**Structure Pattern** :
```python
@dataclass
class Pattern:
    """Pattern d'exécution appris."""
    id: str
    action_sequence: List[ActionType]
    request_types: List[str]  # Types de requêtes où ce pattern est efficace
    success_rate: float  # Taux de succès
    avg_quality_score: float  # Score de qualité moyen
    avg_execution_time: float  # Temps d'exécution moyen
    usage_count: int  # Nombre d'utilisations
    last_used: datetime
```

### 6. MemoryManager (Extension)

**Fichier** : `memory_service/memory_manager.py` (nouveau)

**Responsabilités** :
- Décider quoi mémoriser (au lieu de tout stocker)
- Analyser l'importance des interactions
- Gérer la mémoire de manière sélective
- Nettoyer les souvenirs obsolètes

**Interface** :
```python
class MemoryManager:
    def __init__(self, memory_adapter, config):
        """
        Initialise le gestionnaire de mémoire intelligent.
        """
    
    async def decide_what_to_store(
        self,
        interaction: Dict[str, Any],
        execution_result: ExecutionResult,
        verification_result: VerificationResult
    ) -> List[MemoryItem]:
        """
        Décide quels éléments de l'interaction doivent être mémorisés.
        
        Returns:
            Liste des éléments à mémoriser (peut être vide)
        """
    
    def _analyze_importance(
        self, 
        interaction: Dict[str, Any]
    ) -> float:
        """
        Analyse l'importance d'une interaction.
        """
    
    def _extract_key_information(
        self, 
        interaction: Dict[str, Any]
    ) -> List[str]:
        """
        Extrait les informations clés d'une interaction.
        """
```

---

## Plan d'Implémentation

> **Note d'implémentation actuelle**
>
> Les implémentations concrètes actuelles sont documentées dans :
> - `docs/memory_performing/IMPLEMENTATION_PHASE_EXEMPLE_PROCESS.md` : Phase "exemple_process" (boucle de menus minimale + prompt final canonique, en mode debug)
> - `docs/memory_performing/IMPLEMENTATION_STREAMING_CHUNKS.md` : Système de streaming de chunks et réponses structurées (deux types de réponses, interface web temps réel)
> - `docs/memory_performing/SYSTEME_PATTERNS.md` : Système de patterns pour l'apprentissage des séquences d'actions optimales (version de départ)
>
> Elles servent de base expérimentale avant l'activation progressive de toutes les phases décrites ci-dessous.

### Phase 1 : Infrastructure de Base 

**Objectif** : Mettre en place l'ossature complète (interfaces + boucle cognitive bornée), avec des capacités limitées.

> Clarification d'intention (important)
> - "Construire petit à petit, de complexité croissante" ne signifie pas "simplifier l'architecture".
> - On garde la forme générale (planner → actions → prompt → génération → vérification → boucle),
>   puis on augmente progressivement la richesse : profondeur de décision, types d'actions, heuristiques,
>   apprentissage de patterns, sélection mémoire, etc.

#### 1.1 Structure de Données
- [ ] Créer `core/cognitive_models.py` avec :
  - `ActionPlan`, `Action`, `ActionType`
  - `ExecutionResult`, `VerificationResult`
  - `Pattern`, `RequestAnalysis`
- [ ] Tests unitaires pour les modèles

#### 1.2 CognitivePlanner (Itération 1 : MVP borné, extensible)
- [ ] Créer `core/cognitive_planner.py`
- [ ] Implémenter `plan()` avec arbre de décision initial (statique) mais **profondeur configurable**
- [ ] Implémenter `_analyze_request()` basique (classif. besoins mémoire/identité/outils)
- [ ] Prévoir dès le MVP la notion d'**itération** (plan ajusté en fonction de l'état + résultats précédents)
- [ ] Tests unitaires

#### 1.3 ActionExecutor (Itération 1 : registre d'actions, extensible)
- [ ] Créer `core/action_executor.py`
- [ ] Implémenter `execute_action()` + un registre/dispatch pour actions (architecture extensible)
- [ ] Supporter un premier set d'actions (minimum viable) :
  - `CONSULT_MEMORY`
  - `CONSULT_IDENTITY`
  - `CONSULT_PATTERNS` (même si PatternLearner est rudimentaire au début)
  - `RESPOND`
- [ ] Tests unitaires

#### 1.4 PromptBuilder (Extraction)
- [ ] Extraire logique de `llm_adapter.py` vers `core/prompt_builder.py`
- [ ] Adapter pour utiliser `ExecutionResult`
- [ ] Tests unitaires

**Livrables** :
- Composants de base fonctionnels
- Tests unitaires passants
- Documentation API

---

### Phase 2 : Intégration et Auto-Vérification 

**Objectif** : Intégrer les composants et ajouter l'auto-vérification.

#### 2.1 Intégration dans LLMAdapter
- [ ] Modifier `LLMAdapter.generate()` pour utiliser `CognitivePlanner`
- [ ] Intégrer `ActionExecutor`
- [ ] Intégrer `PromptBuilder`
- [ ] Mode de compatibilité (fallback vers ancien système)

#### 2.2 SelfVerifier
- [ ] Créer `core/self_verifier.py`
- [ ] Implémenter `verify()` avec vérifications de base :
  - Pertinence (distance sémantique)
  - Utilisation mémoire
  - Cohérence identité
- [ ] Tests unitaires

#### 2.3 Tests d'Intégration
- [ ] Tests end-to-end avec scénarios simples
- [ ] Comparaison ancien/nouveau système
- [ ] Métriques de performance

**Livrables** :
- Système intégré fonctionnel
- Auto-vérification opérationnelle
- Tests d'intégration

---

### Phase 3 : Apprentissage de Patterns 

**Objectif** : Ajouter l'apprentissage et l'optimisation des patterns.

#### 3.1 PatternLearner
- [ ] Créer `core/pattern_learner.py`
- [ ] Implémenter stockage des patterns (base de données)
- [ ] Implémenter `record_execution()`
- [ ] Implémenter `get_preferred_patterns()`
- [ ] Tests unitaires

#### 3.2 Intégration PatternLearner
- [ ] Intégrer dans `CognitivePlanner`
- [ ] Utiliser patterns préférés pour guider les décisions
- [ ] Tests d'intégration

#### 3.3 Évaluation et Optimisation
- [ ] Système d'évaluation d'efficacité
- [ ] Mise à jour automatique des patterns préférés
- [ ] Tests de performance

**Livrables** :
- Apprentissage de patterns fonctionnel
- Patterns préférés opérationnels
- Documentation utilisation

---

### Phase 4 : Mémoire Auto-Gérée 

**Objectif** : Implémenter la mémoire sélective et intelligente.

#### 4.1 MemoryManager
- [ ] Créer `memory_service/memory_manager.py`
- [ ] Implémenter `decide_what_to_store()`
- [ ] Implémenter analyse d'importance
- [ ] Implémenter extraction d'informations clés
- [ ] Tests unitaires

#### 4.2 Intégration MemoryManager
- [ ] Intégrer dans le flux principal
- [ ] Remplacer stockage automatique par stockage sélectif
- [ ] Tests d'intégration

#### 4.3 Nettoyage et Optimisation
- [ ] Système de nettoyage automatique
- [ ] Gestion TTL intelligente
- [ ] Compression mémoire

**Livrables** :
- Mémoire auto-gérée fonctionnelle
- Réduction du bruit mémoire
- Tests de validation

---

### Phase 5 : Optimisation et Garde-fous 

**Objectif** : Ajouter les contrôles et optimisations finales.

#### 5.1 Garde-fous
- [ ] Limite de profondeur de décision
- [ ] Budget de réflexion (tokens/temps)
- [ ] Coût d'accès mémoire
- [ ] Détection de boucles cognitives

#### 5.2 Optimisations
- [ ] Cache des décisions fréquentes
- [ ] Parallélisation des actions indépendantes
- [ ] Optimisation des prompts

#### 5.3 Monitoring et Métriques
- [ ] Système de logging détaillé
- [ ] Métriques de performance
- [ ] Dashboard de monitoring (optionnel)

**Livrables** :
- Système robuste avec garde-fous
- Optimisations implémentées
- Documentation complète

---

### Phase 6 : Tests et Documentation 

**Objectif** : Tests exhaustifs et documentation finale.

#### 6.1 Tests
- [ ] Tests de charge
- [ ] Tests de régression
- [ ] Tests de stabilité
- [ ] Tests avec données réelles

#### 6.2 Documentation
- [ ] Documentation utilisateur
- [ ] Documentation développeur
- [ ] Guide de migration
- [ ] Exemples d'utilisation

#### 6.3 Déploiement
- [ ] Préparation déploiement
- [ ] Migration progressive (feature flag)
- [ ] Monitoring post-déploiement

**Livrables** :
- Système testé et documenté
- Prêt pour production
- Guide de migration

---

## Intégration avec l'Existant

### Modifications Requises

#### 1. LLMAdapter (`core/llm_adapter.py`)

**Modifications** :
- Ajouter paramètre `use_cognitive_planner: bool = False` dans `__init__`
- Modifier `generate()` pour utiliser le nouveau système si activé
- Garder l'ancien système comme fallback
- Ajouter un paramètre de **mode de décision** (ex: `cognitive_decision_mode="menu"`)
  - `menu` (défaut) : boucle itérative "proposition d'actions → choix par LIA → exécution → répétition → RESPOND"

**Code exemple** :
```python
async def generate(
    self,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    use_cognitive_planner: bool = False
) -> str:
    """
    Génère une réponse.
    
    Args:
        use_cognitive_planner: Utiliser le nouveau système de planification
    """
    if use_cognitive_planner and self.cognitive_planner:
        return await self._generate_with_planner(message, session_id)
    else:
        return await self._generate_internal(message, context, session_id)
```

#### 2. MemoryAdapter (`memory_service/memory_adapter.py`)

**Extensions** :
- Ajouter méthodes pour recherche avancée
- Ajouter méthodes pour consultation sélective
- Intégrer `MemoryManager` pour stockage sélectif

#### 3. Configuration

**Nouveau fichier** : `config/cognitive_planner.conf`

```ini
[cognitive_planner]
enabled = false
max_depth = 3
reflection_budget_tokens = 500
reflection_budget_time = 2.0
memory_cost_weight = 0.1

[self_verifier]
enabled = true
min_relevance_score = 0.6
min_memory_usage_score = 0.5
min_identity_coherence_score = 0.7
min_overall_score = 0.65

[pattern_learner]
enabled = true
min_success_rate = 0.7
min_usage_count = 5
update_interval_hours = 24

[memory_manager]
enabled = true
min_importance_score = 0.4
auto_cleanup_enabled = true
cleanup_interval_days = 7
```

---

## Garde-fous et Contrôles

### 1. Limite de Profondeur

**Problème** : LIA peut explorer indéfiniment l'arbre de décision.

**Solution** :
- Paramètre `max_depth` dans la configuration
- Arrêt automatique si profondeur atteinte
- Fallback vers un plan **conservateur** (moins coûteux) ou vers le **mode compatibilité** (ancien système)

### 2. Budget de Réflexion

**Problème** : LIA peut consommer trop de tokens/temps pour décider.

**Solution** :
- `reflection_budget_tokens` : Limite de tokens pour la planification
- `reflection_budget_time` : Limite de temps (secondes)
- Arrêt si budget dépassé, utilisation du plan actuel

### 3. Coût d'Accès Mémoire

**Problème** : Trop d'accès mémoire peut ralentir le système.

**Solution** :
- Coût associé à chaque action mémoire
- Plan optimisé pour minimiser les accès
- Cache des résultats fréquents

### 4. Détection de Boucles Cognitives

**Problème** : LIA peut tourner en boucle entre décisions.

**Solution** :
- Historique des décisions prises
- Détection de cycles
- Arrêt et fallback si boucle détectée

### 5. Validation Stricte

**Problème** : Réponses de mauvaise qualité peuvent passer.

**Solution** :
- Seuils minimaux dans `SelfVerifier`
- Re-planification si validation échoue
- Limite de tentatives (ex: 3 max)

---

## Métriques et Évaluation

### Métriques à Suivre

1. **Performance** :
   - Temps de réponse moyen
   - Tokens consommés
   - Nombre d'actions exécutées

2. **Qualité** :
   - Score de pertinence moyen
   - Score d'utilisation mémoire
   - Score de cohérence identité
   - Taux de validation réussie

3. **Efficacité** :
   - Taux de succès des patterns
   - Réduction du bruit mémoire
   - Amélioration de la cohérence long terme

4. **Stabilité** :
   - Nombre de boucles détectées
   - Nombre de fallbacks
   - Erreurs système

### Évaluation

**Comparaison Ancien vs Nouveau Système** :

1. **Test A/B** :
   - Même ensemble de requêtes
   - Comparaison métriques
   - Analyse statistique

2. **Tests Utilisateur** :
   - Feedback utilisateurs
   - Préférence système
   - Satisfaction

3. **Tests Long Terme** :
   - Cohérence sur plusieurs sessions
   - Évolution des patterns
   - Stabilité mémoire

---

## Risques et Mitigation

### Risques Identifiés

1. **Complexité Explosive** (Probabilité: 65%)
   - **Mitigation** : Garde-fous stricts (profondeur, budget)
   - **Monitoring** : Alertes si complexité excessive

2. **Instabilité** (Probabilité: 40%)
   - **Mitigation** : Validation stricte, fallbacks
   - **Monitoring** : Détection de boucles, erreurs

3. **Performance Dégradée** (Probabilité: 50%)
   - **Mitigation** : Optimisations, cache, parallélisation
   - **Monitoring** : Métriques de performance

4. **Mémoire Corrompue** (Probabilité: 20%)
   - **Mitigation** : Validation avant stockage, backups
   - **Monitoring** : Vérification intégrité mémoire

### Plan de Rollback

1. **Feature Flag** : Activation/désactivation facile
2. **Mode Compatibilité** : Ancien système toujours disponible
3. **Migration Progressive** : Par pourcentage d'utilisateurs
4. **Monitoring Continu** : Alertes automatiques

---

## Conclusion

Ce document présente l'architecture technique et le plan d'implémentation pour le système de planification cognitive de LIA. L'approche est progressive et modulaire, permettant une intégration en douceur avec le système existant.

**Prochaines Étapes** :
1. Validation de l'architecture
2. Démarrage Phase 1 (Infrastructure de Base)
3. Itérations et ajustements selon résultats

**Questions Ouvertes** :
- Niveau de profondeur optimal de l'arbre de décision ?
- Seuils de validation optimaux ?
- Fréquence de mise à jour des patterns ?

---

**Document Version** : 1.0  
**Dernière Mise à Jour** : 2024-12-19


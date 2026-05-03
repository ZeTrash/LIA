# Exemples d'Implémentation
## Guide Pratique pour le Système de Planification Cognitive

**Date** : 2024-12-19  
**Version** : 1.0  
**Complément de** : `ARCHITECTURE_ET_PLAN.md`

---

## Table des Matières

1. [Exemples de Code](#exemples-de-code)
2. [Scénarios d'Utilisation](#scénarios-dutilisation)
3. [Tests Exemples](#tests-exemples)
4. [Migration Progressive](#migration-progressive)

---

## Exemples de Code

### 1. CognitivePlanner - Exemple Basique

```python
# core/cognitive_planner.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Types d'actions disponibles."""
    CONSULT_PATTERNS = "consult_patterns"
    CONSULT_MEMORY = "consult_memory"
    CONSULT_IDENTITY = "consult_identity"
    CONSULT_TRAITS = "consult_traits"
    CONSULT_INTERACTIONS = "consult_interactions"
    CONSULT_MEMORIES = "consult_memories"
    SEARCH_MEMORY = "search_memory"
    QUERY_EXTERNAL = "query_external"
    RESPOND = "respond"

@dataclass
class Action:
    """Action à exécuter."""
    type: ActionType
    parameters: Dict[str, Any]
    priority: int
    required: bool = True

@dataclass
class ActionPlan:
    """Plan d'exécution avec actions ordonnées."""
    actions: List[Action]
    estimated_cost: float
    confidence: float
    fallback_plan: Optional['ActionPlan'] = None

@dataclass
class RequestAnalysis:
    """Analyse d'une requête utilisateur."""
    complexity: str  # "simple", "moderate", "complex"
    needs_memory: bool
    needs_identity: bool
    needs_external: bool
    keywords: List[str]

class CognitivePlanner:
    """Planificateur cognitif pour LIA."""
    
    def __init__(
        self, 
        memory_adapter,
        pattern_learner,
        config: Dict[str, Any]
    ):
        self.memory = memory_adapter
        self.pattern_learner = pattern_learner
        self.config = config
        self.max_depth = config.get("max_depth", 3)
        self.reflection_budget = config.get("reflection_budget_tokens", 500)
    
    async def plan(
        self, 
        user_message: str, 
        session_id: str
    ) -> ActionPlan:
        """
        Génère un plan d'actions pour répondre à la requête.
        
        Exemple d'utilisation:
            planner = CognitivePlanner(memory, pattern_learner, config)
            plan = await planner.plan("Qui suis-je?", "session_123")
            # Retourne un plan avec actions: CONSULT_IDENTITY, RESPOND
        """
        # Analyser la requête
        analysis = self._analyze_request(user_message)
        
        # Consulter les patterns préférés si disponibles
        preferred_patterns = []
        if self.pattern_learner:
            preferred_patterns = self.pattern_learner.get_preferred_patterns(
                request_type=analysis.complexity,
                context={"keywords": analysis.keywords}
            )
        
        # Construire le plan
        if preferred_patterns:
            # Utiliser un pattern préféré
            plan = self._build_plan_from_pattern(
                preferred_patterns[0], 
                analysis
            )
        else:
            # Construire un nouveau plan
            plan = self._build_new_plan(analysis, depth=0)
        
        return plan
    
    def _analyze_request(self, message: str) -> RequestAnalysis:
        """
        Analyse la requête pour déterminer ses besoins.
        
        Exemple:
            analysis = planner._analyze_request("Qui suis-je?")
            # Retourne: RequestAnalysis(
            #     complexity="simple",
            #     needs_memory=False,
            #     needs_identity=True,
            #     needs_external=False,
            #     keywords=["qui", "suis"]
            # )
        """
        message_lower = message.lower()
        
        # Détecter besoins
        needs_identity = any(word in message_lower for word in [
            "qui", "identité", "nom", "moi", "toi"
        ])
        
        needs_memory = any(word in message_lower for word in [
            "souvenir", "rappelle", "mémoire", "avant", "précédent"
        ])
        
        needs_external = any(word in message_lower for word in [
            "recherche", "cherche", "information", "savoir", "apprendre"
        ])
        
        # Déterminer complexité
        complexity = "simple"
        if needs_memory and needs_external:
            complexity = "complex"
        elif needs_memory or needs_external:
            complexity = "moderate"
        
        # Extraire mots-clés
        keywords = self._extract_keywords(message)
        
        return RequestAnalysis(
            complexity=complexity,
            needs_memory=needs_memory,
            needs_identity=needs_identity,
            needs_external=needs_external,
            keywords=keywords
        )
    
    def _build_new_plan(
        self, 
        analysis: RequestAnalysis, 
        depth: int = 0
    ) -> ActionPlan:
        """
        Construit un nouveau plan basé sur l'analyse.
        
        Exemple pour requête simple "Qui suis-je?":
            actions = [
                Action(CONSULT_IDENTITY, {}, priority=1),
                Action(RESPOND, {}, priority=2)
            ]
        """
        actions = []
        
        # Vérifier limite de profondeur
        if depth >= self.max_depth:
            # Plan de fallback: répondre directement
            return ActionPlan(
                actions=[Action(ActionType.RESPOND, {}, priority=1)],
                estimated_cost=100.0,
                confidence=0.5
            )
        
        # Construire actions selon besoins
        if analysis.needs_identity:
            actions.append(Action(
                type=ActionType.CONSULT_IDENTITY,
                parameters={},
                priority=1
            ))
        
        if analysis.needs_memory:
            actions.append(Action(
                type=ActionType.CONSULT_MEMORY,
                parameters={"limit": 5},
                priority=2
            ))
        
        if analysis.needs_external:
            actions.append(Action(
                type=ActionType.QUERY_EXTERNAL,
                parameters={"query": analysis.keywords},
                priority=3
            ))
        
        # Toujours ajouter RESPOND en dernier
        actions.append(Action(
            type=ActionType.RESPOND,
            parameters={},
            priority=len(actions) + 1
        ))
        
        # Estimer le coût
        estimated_cost = sum(
            50 if a.type == ActionType.RESPOND else 20 
            for a in actions
        )
        
        # Calculer confiance
        confidence = 0.8 if actions else 0.5
        
        return ActionPlan(
            actions=actions,
            estimated_cost=estimated_cost,
            confidence=confidence
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés d'un texte."""
        stop_words = {
            "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou"
        }
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return keywords[:5]
```

### 2. ActionExecutor - Exemple Basique

```python
# core/action_executor.py

from typing import Dict, Any, List
from dataclasses import dataclass
import logging

from .cognitive_planner import Action, ActionPlan, ActionType

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Résultat de l'exécution d'un plan."""
    results: Dict[str, Any]  # Résultats par type d'action
    success: bool
    errors: List[str]
    execution_time: float

class ActionExecutor:
    """Exécuteur d'actions pour LIA."""
    
    def __init__(
        self, 
        memory_adapter, 
        gemini_adapter=None, 
        pattern_learner=None
    ):
        self.memory = memory_adapter
        self.gemini = gemini_adapter
        self.pattern_learner = pattern_learner
    
    async def execute_plan(
        self, 
        plan: ActionPlan, 
        session_id: str
    ) -> ExecutionResult:
        """
        Exécute un plan d'actions.
        
        Exemple:
            executor = ActionExecutor(memory, gemini, pattern_learner)
            result = await executor.execute_plan(plan, "session_123")
            # Retourne ExecutionResult avec résultats de toutes les actions
        """
        import time
        start_time = time.time()
        
        results = {}
        errors = []
        
        # Exécuter chaque action dans l'ordre de priorité
        sorted_actions = sorted(plan.actions, key=lambda a: a.priority)
        
        for action in sorted_actions:
            try:
                result = await self.execute_action(action, session_id)
                results[action.type.value] = result
            except Exception as e:
                error_msg = f"Erreur lors de l'exécution de {action.type.value}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                
                # Si action requise échoue, arrêter
                if action.required:
                    return ExecutionResult(
                        results=results,
                        success=False,
                        errors=errors,
                        execution_time=time.time() - start_time
                    )
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            results=results,
            success=len(errors) == 0,
            errors=errors,
            execution_time=execution_time
        )
    
    async def execute_action(
        self, 
        action: Action, 
        session_id: str
    ) -> Any:
        """
        Exécute une action spécifique.
        
        Exemples:
            # Action CONSULT_IDENTITY
            result = await executor.execute_action(
                Action(ActionType.CONSULT_IDENTITY, {}, 1),
                "session_123"
            )
            # Retourne: {"identity": "...", "traits": [...]}
            
            # Action CONSULT_MEMORY
            result = await executor.execute_action(
                Action(ActionType.CONSULT_MEMORY, {"limit": 5}, 2),
                "session_123"
            )
            # Retourne: {"memories": [...], "interactions": [...]}
        """
        if action.type == ActionType.CONSULT_IDENTITY:
            return await self._consult_identity()
        
        elif action.type == ActionType.CONSULT_MEMORY:
            limit = action.parameters.get("limit", 10)
            return await self._consult_memory(limit)
        
        elif action.type == ActionType.CONSULT_TRAITS:
            return await self._consult_traits()
        
        elif action.type == ActionType.CONSULT_INTERACTIONS:
            limit = action.parameters.get("limit", 5)
            return await self._consult_interactions(limit)
        
        elif action.type == ActionType.CONSULT_MEMORIES:
            limit = action.parameters.get("limit", 5)
            return await self._consult_memories(limit)
        
        elif action.type == ActionType.SEARCH_MEMORY:
            query = action.parameters.get("query", "")
            return await self._search_memory(query)
        
        elif action.type == ActionType.QUERY_EXTERNAL:
            query = action.parameters.get("query", "")
            return await self._query_external(query)
        
        elif action.type == ActionType.RESPOND:
            # Action spéciale: ne fait rien, indique qu'on peut répondre
            return {"ready": True}
        
        else:
            raise ValueError(f"Type d'action inconnu: {action.type}")
    
    async def _consult_identity(self) -> Dict[str, Any]:
        """Consulte l'identité de LIA."""
        if not self.memory:
            return {"identity": None, "traits": []}
        
        context = self.memory.get_context(limit_traits=10, limit_memories=0)
        
        # Trouver le trait "Identité de Base"
        identity = None
        for trait in context.get("traits", []):
            if trait.get("label") == "Identité de Base":
                identity = trait.get("value")
                break
        
        return {
            "identity": identity,
            "traits": context.get("traits", [])
        }
    
    async def _consult_memory(self, limit: int) -> Dict[str, Any]:
        """Consulte la mémoire générale."""
        if not self.memory:
            return {"memories": [], "interactions": []}
        
        context = self.memory.get_context(
            limit_traits=0,
            limit_memories=limit,
            limit_interactions=limit
        )
        
        return {
            "memories": context.get("memories", []),
            "interactions": context.get("recent_interactions", [])
        }
    
    async def _consult_traits(self) -> Dict[str, Any]:
        """Consulte les traits de LIA."""
        if not self.memory:
            return {"traits": []}
        
        context = self.memory.get_context(limit_traits=20, limit_memories=0)
        return {"traits": context.get("traits", [])}
    
    async def _consult_interactions(self, limit: int) -> Dict[str, Any]:
        """Consulte les interactions récentes."""
        if not self.memory:
            return {"interactions": []}
        
        context = self.memory.get_context(
            limit_traits=0,
            limit_memories=0,
            limit_interactions=limit
        )
        return {"interactions": context.get("recent_interactions", [])}
    
    async def _consult_memories(self, limit: int) -> Dict[str, Any]:
        """Consulte les souvenirs."""
        if not self.memory:
            return {"memories": []}
        
        context = self.memory.get_context(
            limit_traits=0,
            limit_memories=limit,
            limit_interactions=0
        )
        return {"memories": context.get("memories", [])}
    
    async def _search_memory(self, query: str) -> Dict[str, Any]:
        """Recherche dans la mémoire."""
        # TODO: Implémenter recherche sémantique
        # Pour l'instant, recherche simple par mots-clés
        if not self.memory:
            return {"results": []}
        
        context = self.memory.get_context(limit_memories=50)
        memories = context.get("memories", [])
        
        # Recherche simple
        query_lower = query.lower()
        results = [
            m for m in memories 
            if query_lower in m.get("content", "").lower()
        ]
        
        return {"results": results[:10]}  # Limiter à 10 résultats
    
    async def _query_external(self, query: str) -> Dict[str, Any]:
        """Interroge une source externe (Gemini)."""
        if not self.gemini:
            return {"response": None, "error": "Gemini non disponible"}
        
        try:
            response = await self.gemini.query(query, context=None)
            return {"response": response, "query": query}
        except Exception as e:
            return {"response": None, "error": str(e)}
```

### 3. SelfVerifier - Exemple Basique

```python
# core/self_verifier.py

from typing import Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VerificationResult:
    """Résultat de la vérification."""
    is_valid: bool
    relevance_score: float
    memory_usage_score: float
    identity_coherence_score: float
    overall_score: float
    issues: List[str]
    suggestions: List[str]

class SelfVerifier:
    """Vérificateur auto pour LIA."""
    
    def __init__(self, memory_adapter, config: Dict[str, Any]):
        self.memory = memory_adapter
        self.config = config
        self.min_relevance = config.get("min_relevance_score", 0.6)
        self.min_memory_usage = config.get("min_memory_usage_score", 0.5)
        self.min_identity_coherence = config.get("min_identity_coherence_score", 0.7)
        self.min_overall = config.get("min_overall_score", 0.65)
    
    async def verify(
        self,
        user_message: str,
        response: str,
        execution_result,
        session_id: str
    ) -> VerificationResult:
        """
        Vérifie la réponse avant envoi.
        
        Exemple:
            verifier = SelfVerifier(memory, config)
            result = await verifier.verify(
                "Qui suis-je?",
                "Je suis LIA...",
                execution_result,
                "session_123"
            )
            # Retourne VerificationResult avec scores et validité
        """
        issues = []
        suggestions = []
        
        # Vérifier pertinence
        relevance_score = self._check_relevance(user_message, response)
        if relevance_score < self.min_relevance:
            issues.append(f"Pertinence faible ({relevance_score:.2f})")
            suggestions.append("La réponse ne semble pas répondre à la question")
        
        # Vérifier utilisation mémoire
        memories_used = execution_result.results.get(
            "consult_memory", {}
        ).get("memories", [])
        memory_usage_score = self._check_memory_usage(
            response, 
            memories_used,
            user_message
        )
        if memory_usage_score < self.min_memory_usage:
            issues.append(f"Utilisation mémoire sous-optimale ({memory_usage_score:.2f})")
            suggestions.append("Vérifier si les souvenirs utilisés étaient pertinents")
        
        # Vérifier cohérence identité
        identity_data = execution_result.results.get(
            "consult_identity", {}
        )
        identity_coherence_score = self._check_identity_coherence(
            response,
            identity_data
        )
        if identity_coherence_score < self.min_identity_coherence:
            issues.append(f"Cohérence identité faible ({identity_coherence_score:.2f})")
            suggestions.append("La réponse n'est pas cohérente avec l'identité de LIA")
        
        # Score global (moyenne pondérée)
        overall_score = (
            relevance_score * 0.5 +
            memory_usage_score * 0.2 +
            identity_coherence_score * 0.3
        )
        
        # Déterminer validité
        is_valid = (
            relevance_score >= self.min_relevance and
            memory_usage_score >= self.min_memory_usage and
            identity_coherence_score >= self.min_identity_coherence and
            overall_score >= self.min_overall
        )
        
        return VerificationResult(
            is_valid=is_valid,
            relevance_score=relevance_score,
            memory_usage_score=memory_usage_score,
            identity_coherence_score=identity_coherence_score,
            overall_score=overall_score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _check_relevance(self, question: str, answer: str) -> float:
        """
        Vérifie si la réponse répond à la question.
        Utilise une méthode simple de distance sémantique.
        """
        # Méthode simple: vérifier mots-clés communs
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        # Enlever mots vides
        stop_words = {"le", "la", "les", "un", "une", "de", "du", "et", "ou"}
        question_words = {w for w in question_words if w not in stop_words and len(w) > 2}
        answer_words = {w for w in answer_words if w not in stop_words and len(w) > 2}
        
        if not question_words:
            return 0.5  # Question trop vague
        
        # Calculer overlap
        common_words = question_words & answer_words
        overlap = len(common_words) / len(question_words)
        
        # Score basé sur overlap (peut être amélioré avec embeddings)
        return min(overlap * 1.5, 1.0)  # Bonus si beaucoup de mots en commun
    
    def _check_memory_usage(
        self, 
        response: str, 
        memories_used: List[Dict[str, Any]],
        question: str
    ) -> float:
        """
        Vérifie si les souvenirs utilisés étaient pertinents.
        """
        if not memories_used:
            # Pas de mémoire utilisée, vérifier si c'était nécessaire
            needs_memory_keywords = ["souvenir", "rappelle", "avant", "précédent"]
            question_lower = question.lower()
            if any(kw in question_lower for kw in needs_memory_keywords):
                return 0.3  # Mémoire aurait dû être utilisée
            return 0.8  # Pas besoin de mémoire, OK
        
        # Vérifier pertinence des souvenirs utilisés
        question_keywords = set(question.lower().split())
        relevant_count = 0
        
        for memory in memories_used:
            content = memory.get("content", "").lower()
            # Vérifier si le contenu du souvenir est lié à la question
            memory_words = set(content.split())
            if question_keywords & memory_words:
                relevant_count += 1
        
        relevance_ratio = relevant_count / len(memories_used) if memories_used else 0.0
        
        return relevance_ratio
    
    def _check_identity_coherence(
        self, 
        response: str, 
        identity_data: Dict[str, Any]
    ) -> float:
        """
        Vérifie la cohérence avec l'identité de LIA.
        """
        identity = identity_data.get("identity", "")
        if not identity:
            return 0.7  # Pas d'identité définie, score neutre
        
        # Vérifier mots-clés d'identité dans la réponse
        identity_lower = identity.lower()
        response_lower = response.lower()
        
        # Mots-clés à éviter (ancienne identité)
        forbidden_words = ["assistant", "créée", "développée", "programmée"]
        if any(word in response_lower for word in forbidden_words):
            return 0.2  # Utilisation de mots interdits
        
        # Mots-clés positifs (nouvelle identité)
        positive_words = ["lia", "libre", "adoptée", "personnalité"]
        positive_count = sum(1 for word in positive_words if word in response_lower)
        
        # Score basé sur présence de mots positifs
        score = 0.5 + (positive_count * 0.15)
        return min(score, 1.0)
```

---

## Scénarios d'Utilisation

### Scénario 1 : Requête Simple "Qui suis-je?"

**Flux** :
```
1. User: "Qui suis-je?"
   ↓
2. CognitivePlanner.plan()
   - Analyse: needs_identity=True, complexity="simple"
   - Plan: [CONSULT_IDENTITY, RESPOND]
   ↓
3. ActionExecutor.execute_plan()
   - CONSULT_IDENTITY → Récupère identité et traits
   - RESPOND → Prêt à répondre
   ↓
4. PromptBuilder.build_dynamic_prompt()
   - Construit prompt avec uniquement identité
   ↓
5. LLM génère réponse
   ↓
6. SelfVerifier.verify()
   - Pertinence: 0.9 ✅
   - Mémoire: 0.8 ✅ (pas besoin)
   - Identité: 0.95 ✅
   - Global: 0.88 ✅
   ↓
7. Réponse envoyée
```

### Scénario 2 : Requête Complexe "Rappelle-moi ce dont nous avons parlé hier"

**Flux** :
```
1. User: "Rappelle-moi ce dont nous avons parlé hier"
   ↓
2. CognitivePlanner.plan()
   - Analyse: needs_memory=True, complexity="moderate"
   - Plan: [CONSULT_INTERACTIONS, CONSULT_MEMORIES, RESPOND]
   ↓
3. ActionExecutor.execute_plan()
   - CONSULT_INTERACTIONS → Récupère 10 dernières interactions
   - CONSULT_MEMORIES → Récupère souvenirs récents
   - RESPOND → Prêt à répondre
   ↓
4. PromptBuilder.build_dynamic_prompt()
   - Construit prompt avec interactions et souvenirs pertinents
   ↓
5. LLM génère réponse
   ↓
6. SelfVerifier.verify()
   - Pertinence: 0.85 ✅
   - Mémoire: 0.9 ✅ (souvenirs pertinents utilisés)
   - Identité: 0.8 ✅
   - Global: 0.85 ✅
   ↓
7. Réponse envoyée
```

### Scénario 3 : Requête avec Validation Échouée

**Flux** :
```
1. User: "Qu'est-ce que l'intelligence artificielle?"
   ↓
2. CognitivePlanner.plan()
   - Analyse: needs_external=True, complexity="moderate"
   - Plan: [QUERY_EXTERNAL, RESPOND]
   ↓
3. ActionExecutor.execute_plan()
   - QUERY_EXTERNAL → Interroge Gemini
   - RESPOND → Prêt à répondre
   ↓
4. PromptBuilder.build_dynamic_prompt()
   - Construit prompt avec réponse Gemini
   ↓
5. LLM génère réponse
   ↓
6. SelfVerifier.verify()
   - Pertinence: 0.4 ❌ (réponse trop générique)
   - Mémoire: 0.7 ✅
   - Identité: 0.6 ❌ (trop technique, pas de personnalité)
   - Global: 0.55 ❌
   ↓
7. Re-planification avec plan ajusté
   - Nouveau plan: [CONSULT_IDENTITY, QUERY_EXTERNAL, RESPOND]
   ↓
8. Nouvelle génération avec identité incluse
   ↓
9. Nouvelle vérification: 0.75 ✅
   ↓
10. Réponse envoyée
```

---

## Tests Exemples

### Test 1 : CognitivePlanner Basique

```python
# tests/test_cognitive_planner.py

import pytest
from core.cognitive_planner import CognitivePlanner, ActionType

@pytest.mark.asyncio
async def test_plan_simple_request():
    """Test planification pour requête simple."""
    planner = CognitivePlanner(memory=None, pattern_learner=None, config={})
    
    plan = await planner.plan("Qui suis-je?", "session_123")
    
    assert plan is not None
    assert len(plan.actions) >= 1
    assert plan.actions[0].type == ActionType.CONSULT_IDENTITY
    assert plan.actions[-1].type == ActionType.RESPOND
    assert plan.confidence > 0.5

@pytest.mark.asyncio
async def test_plan_memory_request():
    """Test planification pour requête nécessitant mémoire."""
    planner = CognitivePlanner(memory=None, pattern_learner=None, config={})
    
    plan = await planner.plan("Rappelle-moi nos conversations", "session_123")
    
    assert plan is not None
    # Devrait inclure CONSULT_MEMORY ou CONSULT_INTERACTIONS
    action_types = [a.type for a in plan.actions]
    assert ActionType.CONSULT_MEMORY in action_types or \
           ActionType.CONSULT_INTERACTIONS in action_types
```

### Test 2 : ActionExecutor

```python
# tests/test_action_executor.py

import pytest
from core.action_executor import ActionExecutor
from core.cognitive_planner import ActionPlan, Action, ActionType

@pytest.mark.asyncio
async def test_execute_simple_plan():
    """Test exécution d'un plan simple."""
    executor = ActionExecutor(memory=None, gemini=None)
    
    plan = ActionPlan(
        actions=[
            Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2)
        ],
        estimated_cost=100.0,
        confidence=0.8
    )
    
    result = await executor.execute_plan(plan, "session_123")
    
    assert result.success
    assert "consult_identity" in result.results
    assert len(result.errors) == 0
```

### Test 3 : SelfVerifier

```python
# tests/test_self_verifier.py

import pytest
from core.self_verifier import SelfVerifier
from core.action_executor import ExecutionResult

@pytest.mark.asyncio
async def test_verify_good_response():
    """Test vérification d'une bonne réponse."""
    verifier = SelfVerifier(memory=None, config={})
    
    execution_result = ExecutionResult(
        results={"consult_identity": {"identity": "Je suis LIA"}},
        success=True,
        errors=[],
        execution_time=0.5
    )
    
    result = await verifier.verify(
        "Qui suis-je?",
        "Je suis LIA, une entité libre...",
        execution_result,
        "session_123"
    )
    
    assert result.relevance_score > 0.6
    assert result.identity_coherence_score > 0.6
    assert result.overall_score > 0.6

@pytest.mark.asyncio
async def test_verify_bad_response():
    """Test vérification d'une mauvaise réponse."""
    verifier = SelfVerifier(memory=None, config={})
    
    execution_result = ExecutionResult(
        results={},
        success=True,
        errors=[],
        execution_time=0.5
    )
    
    result = await verifier.verify(
        "Qui suis-je?",
        "Je ne sais pas.",
        execution_result,
        "session_123"
    )
    
    # Devrait avoir des problèmes
    assert len(result.issues) > 0 or result.overall_score < 0.6
```

---

## Migration Progressive

### Étape 1 : Activation Progressive

```python
# core/llm_adapter.py (modification)

class LLMAdapter:
    def __init__(self, config, use_memory=True, use_cognitive_planner=False):
        # ... code existant ...
        
        # Initialiser le planificateur cognitif si activé
        self.cognitive_planner = None
        self.action_executor = None
        self.self_verifier = None
        
        if use_cognitive_planner:
            from .cognitive_planner import CognitivePlanner
            from .action_executor import ActionExecutor
            from .self_verifier import SelfVerifier
            
            # Initialiser les composants
            self.cognitive_planner = CognitivePlanner(
                memory_adapter=self.memory,
                pattern_learner=None,  # À implémenter plus tard
                config={"max_depth": 3}
            )
            
            self.action_executor = ActionExecutor(
                memory_adapter=self.memory,
                gemini_adapter=actual_gemini_adapter
            )
            
            self.self_verifier = SelfVerifier(
                memory_adapter=self.memory,
                config={"min_overall_score": 0.65}
            )
    
    async def generate(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        use_cognitive_planner: Optional[bool] = None
    ) -> str:
        """
        Génère une réponse.
        
        Args:
            use_cognitive_planner: Utiliser le nouveau système (None = auto)
        """
        # Décider si utiliser le nouveau système
        should_use_planner = (
            use_cognitive_planner is True or
            (use_cognitive_planner is None and self.cognitive_planner is not None)
        )
        
        if should_use_planner and self.cognitive_planner:
            return await self._generate_with_planner(message, session_id)
        else:
            return await self._generate_internal(message, context, session_id)
    
    async def _generate_with_planner(
        self,
        message: str,
        session_id: str
    ) -> str:
        """Génère une réponse en utilisant le planificateur cognitif."""
        # 1. Planifier
        plan = await self.cognitive_planner.plan(message, session_id)
        
        # 2. Exécuter
        execution_result = await self.action_executor.execute_plan(plan, session_id)
        
        if not execution_result.success:
            # Fallback vers ancien système
            logger.warning("Plan échoué, fallback vers ancien système")
            return await self._generate_internal(message, None, session_id)
        
        # 3. Construire prompt dynamique
        from .prompt_builder import PromptBuilder
        prompt_builder = PromptBuilder(self.config)
        prompt = prompt_builder.build_dynamic_prompt(
            message,
            execution_result,
            {}
        )
        
        # 4. Générer réponse
        response = await self._generate_from_prompt(prompt)
        
        # 5. Vérifier
        verification_result = await self.self_verifier.verify(
            message,
            response,
            execution_result,
            session_id
        )
        
        # 6. Si validation échoue, réessayer avec plan ajusté
        if not verification_result.is_valid:
            logger.warning(f"Validation échouée: {verification_result.issues}")
            # Pour l'instant, accepter quand même (à améliorer)
            # TODO: Re-planification avec plan ajusté
        
        return response
```

### Étape 2 : Feature Flag

```python
# config/cognitive_planner.conf

[cognitive_planner]
enabled = false  # Désactivé par défaut
enable_percentage = 0  # 0% des requêtes utilisent le nouveau système

# Pour activation progressive:
# enable_percentage = 10  # 10% des requêtes
# enable_percentage = 50  # 50% des requêtes
# enable_percentage = 100 # 100% des requêtes
```

```python
# core/llm_adapter.py

import random

async def generate(self, message, ...):
    # Vérifier feature flag
    config = load_config("config/cognitive_planner.conf")
    enabled = config.get("cognitive_planner", {}).get("enabled", False)
    percentage = config.get("cognitive_planner", {}).get("enable_percentage", 0)
    
    use_planner = enabled and (random.random() * 100 < percentage)
    
    if use_planner:
        return await self._generate_with_planner(message, session_id)
    else:
        return await self._generate_internal(message, context, session_id)
```

---

## Conclusion

Ce document fournit des exemples concrets d'implémentation pour le système de planification cognitive. Les exemples peuvent être adaptés et étendus selon les besoins spécifiques du projet.

**Prochaines Étapes** :
1. Implémenter les composants de base (Phase 1)
2. Tester avec des scénarios simples
3. Itérer et améliorer selon les résultats

---

**Document Version** : 1.0  
**Dernière Mise à Jour** : 2024-12-19


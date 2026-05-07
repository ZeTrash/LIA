"""ActionExecutor: execute Actions/ActionPlans to build context for LIA.

This executor is intentionally tool-oriented:
- safe even if memory/gemini are unavailable
- does not require running the LLM (it only executes tool/memory steps)

In "menu mode", the orchestrator can call `execute_action()` step-by-step.
In "heuristic mode", the orchestrator calls `execute_plan()` for a full plan.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .cognitive_models import Action, ActionPlan, ActionType, ExecutionResult
from .environment_awareness import Capability

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Execute actions against memory / external tools to build context."""

    def __init__(self, memory_adapter: Any = None, gemini_adapter: Any = None, pattern_learner: Any = None, environment_awareness: Any = None):
        self.memory = memory_adapter
        self.gemini = gemini_adapter
        self.pattern_learner = pattern_learner
        self.environment_awareness = environment_awareness

    async def execute_plan(self, plan: ActionPlan, session_id: str = "default") -> ExecutionResult:
        logger.info(f"⚙️  [EXECUTOR] Début exécution du plan: {len(plan.actions)} actions (session: {session_id})")
        start = time.time()
        results: Dict[str, Any] = {}
        errors: List[str] = []

        for idx, action in enumerate(plan.sorted_actions(), 1):
            logger.debug(f"  🔄 [EXECUTOR] Exécution action {idx}/{len(plan.actions)}: {action.type.value} (priority: {action.priority})")
            try:
                action_start = time.time()
                res = await self.execute_action(action, session_id=session_id, partial_results=results)
                action_time = time.time() - action_start
                results[action.type.value] = res
                logger.debug(f"  ✅ [EXECUTOR] Action {action.type.value} exécutée en {action_time:.3f}s")
            except Exception as e:
                msg = f"Error executing {action.type.value}: {e}"
                errors.append(msg)
                logger.error(f"  ❌ [EXECUTOR] Erreur lors de l'exécution de {action.type.value}: {e}")
                if action.required:
                    logger.warning(f"  ⚠️  [EXECUTOR] Action requise échouée, arrêt de l'exécution")
                    return ExecutionResult(
                        results=results,
                        success=False,
                        errors=errors,
                        execution_time=time.time() - start,
                    )

        total_time = time.time() - start
        success = len(errors) == 0
        logger.info(f"{'✅' if success else '⚠️ '} [EXECUTOR] Exécution terminée: {len(results)} résultats, {len(errors)} erreurs, temps={total_time:.3f}s")
        return ExecutionResult(results=results, success=success, errors=errors, execution_time=total_time)

    async def execute_action(
        self,
        action: Action,
        session_id: str = "default",
        partial_results: Optional[Dict[str, Any]] = None,
    ) -> Any:
        _ = session_id
        _ = partial_results or {}

        if action.type == ActionType.CONSULT_PATTERNS:
            logger.debug(f"    📋 [EXECUTOR] Consultation des patterns...")
            return self._consult_patterns(action.parameters)

        if action.type == ActionType.CONSULT_REQUEST:
            # Expose the user request only if the agent chose to consult it.
            req = str(action.parameters.get("request", "") or "")
            logger.debug(f"    📨 [EXECUTOR] Consultation de la demande utilisateur (len={len(req)})...")
            return {"request": req}

        if action.type == ActionType.CONSULT_IDENTITY:
            logger.debug(f"    👤 [EXECUTOR] Consultation de l'identité...")
            result = self._consult_identity()
            logger.debug(f"    ✅ [EXECUTOR] Identité récupérée: {result.get('identity') is not None}, {len(result.get('traits', []))} traits")
            return result

        if action.type == ActionType.CONSULT_TRAITS:
            limit = int(action.parameters.get("limit", 20))
            logger.debug(f"    🎭 [EXECUTOR] Consultation des traits (limit: {limit})...")
            return self._consult_traits(limit=limit)

        if action.type == ActionType.CONSULT_ENVIRONMENT:
            logger.debug("    🧰 [EXECUTOR] Consultation de l'environnement/capacités...")
            if self.environment_awareness:
                # Utiliser EnvironmentAwareness pour obtenir les capacités réelles
                capabilities_list = []
                if self.environment_awareness.can_use(Capability.MEMORY):
                    capabilities_list.append("Mémoire persistante (stockage et récupération de souvenirs, personnalité, objectifs)")
                if self.environment_awareness.can_use(Capability.GEMINI):
                    capabilities_list.append("Accès à Gemini (source de connaissances externes, débats, informations)")
                if self.environment_awareness.can_use(Capability.USER_INTERACTION):
                    capabilities_list.append("Interaction avec l'utilisateur (questions, échanges, apprentissage)")
                if self.environment_awareness.can_use(Capability.LEARNING):
                    capabilities_list.append("Apprentissage et amélioration continue")
                if self.environment_awareness.can_use(Capability.DEBATE):
                    capabilities_list.append("Débat et discussion approfondie")
                
                env_desc = self.environment_awareness.get_environment_description()
                return {
                    "capabilities": capabilities_list,
                    "description": env_desc,
                    "notes": "Je suis autonome : je peux décider quand utiliser ma mémoire, quand solliciter Gemini, et quand demander des clarifications à l'utilisateur.",
                }
            else:
                # Fallback si EnvironmentAwareness n'est pas disponible
                return {
                    "capabilities": [
                        "Planification par menus (choix internes)",
                        "Consultation mémoire (si disponible)",
                        "Requête externe Gemini (si configuré)",
                        "Génération de réponse finale",
                    ],
                    "notes": "Ces capacités peuvent dépendre de la configuration locale (adapters disponibles).",
                }

        if action.type == ActionType.CONSULT_MEMORY:
            limit = int(action.parameters.get("limit", 5))
            logger.debug(f"    💭 [EXECUTOR] Consultation mémoire générale (limit: {limit})...")
            result = self._consult_memory(limit=limit)
            logger.debug(f"    ✅ [EXECUTOR] Mémoire récupérée: {len(result.get('memories', []))} mémoires, {len(result.get('recent_interactions', []))} interactions")
            return result

        if action.type == ActionType.CONSULT_INTERACTIONS:
            limit = int(action.parameters.get("limit", 5))
            logger.debug(f"    💬 [EXECUTOR] Consultation interactions (limit: {limit})...")
            result = self._consult_interactions(limit=limit)
            logger.debug(f"    ✅ [EXECUTOR] Interactions récupérées: {len(result.get('recent_interactions', []))}")
            return result

        if action.type == ActionType.CONSULT_MEMORIES:
            limit = int(action.parameters.get("limit", 5))
            logger.debug(f"    📚 [EXECUTOR] Consultation mémoires (limit: {limit})...")
            result = self._consult_memories(limit=limit)
            logger.debug(f"    ✅ [EXECUTOR] Mémoires récupérées: {len(result.get('memories', []))}")
            return result

        if action.type == ActionType.CONSULT_OBJECTIVES:
            logger.debug("    🎯 [EXECUTOR] Consultation des objectifs...")
            return self._consult_objectives()

        if action.type == ActionType.CONSULT_RECENT_EPISODES:
            limit = int(action.parameters.get("limit", 5))
            logger.debug(f"    🕒 [EXECUTOR] Consultation épisodes récents (limit: {limit})...")
            return self._consult_recent_episodes(limit=limit)

        if action.type == ActionType.SEARCH_BY_EMOTION:
            emotion = str(action.parameters.get("emotion", "")).strip()
            limit = int(action.parameters.get("limit", 10))
            logger.debug(f"    ❤️ [EXECUTOR] Recherche par émotion='{emotion}' (limit: {limit})...")
            return self._search_by_emotion(emotion=emotion, limit=limit)

        if action.type == ActionType.SEARCH_MEMORY:
            query = str(action.parameters.get("query", "")).strip()
            limit = int(action.parameters.get("limit", 10))
            logger.debug(f"    🔍 [EXECUTOR] Recherche mémoire: '{query[:30]}...' (limit: {limit})...")
            result = self._search_memory(query=query, limit=limit)
            logger.debug(f"    ✅ [EXECUTOR] Recherche terminée: {len(result.get('results', []))} résultats")
            return result

        if action.type == ActionType.QUERY_EXTERNAL:
            # Optional: only if gemini adapter exists
            query = str(action.parameters.get("query", "")).strip()
            logger.info(f"    🌐 [EXECUTOR] Requête externe (Gemini): '{query[:50]}...'...")
            result = await self._query_external(query=query)
            if result.get("available"):
                logger.info(f"    ✅ [EXECUTOR] Réponse externe reçue ({len(str(result.get('response', '')))} caractères)")
            else:
                logger.warning(f"    ⚠️  [EXECUTOR] Requête externe non disponible: {result.get('error', 'N/A')}")
            return result

        if action.type == ActionType.NAVIGATE_GENERAL:
            logger.debug("    🧭 [EXECUTOR] Navigation vers le menu général")
            return {"menu_state": "general"}

        if action.type == ActionType.NAVIGATE_BASE:
            logger.debug("    🧭 [EXECUTOR] Navigation vers le menu de base")
            return {"menu_state": "base"}

        if action.type == ActionType.RESPOND:
            logger.debug(f"    ✅ [EXECUTOR] Prêt à répondre")
            return {"ready": True}

        raise ValueError(f"Unknown action type: {action.type}")

    def _consult_patterns(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if not self.pattern_learner:
            return {"patterns": [], "available": False}
        try:
            request_type = parameters.get("request_type", "unknown")
            context = parameters.get("context", {})
            patterns = self.pattern_learner.get_preferred_patterns(request_type=request_type, context=context)
            return {"patterns": patterns, "available": True}
        except Exception as e:
            return {"patterns": [], "available": False, "error": str(e)}

    def _consult_identity(self) -> Dict[str, Any]:
        if not self.memory:
            return {"identity": None, "traits": []}

        context = self.memory.get_context(limit_traits=20, limit_memories=0, limit_interactions=0)
        identity_value = None
        for trait in context.get("traits", []) or []:
            if trait.get("label") == "Identité de Base":
                identity_value = trait.get("value")
                break

        return {"identity": identity_value, "traits": context.get("traits", []) or []}

    def _consult_traits(self, limit: int = 20) -> Dict[str, Any]:
        if not self.memory:
            return {"traits": []}
        context = self.memory.get_context(limit_traits=limit, limit_memories=0, limit_interactions=0)
        return {"traits": context.get("traits", []) or []}

    def _consult_memory(self, limit: int = 5) -> Dict[str, Any]:
        """General memory context (memories + recent interactions)."""
        if not self.memory:
            return {"memories": [], "recent_interactions": []}
        context = self.memory.get_context(limit_traits=0, limit_memories=limit, limit_interactions=limit)
        return {
            "memories": context.get("memories", []) or [],
            "recent_interactions": context.get("recent_interactions", []) or [],
        }

    def _consult_interactions(self, limit: int = 5) -> Dict[str, Any]:
        if not self.memory:
            return {"recent_interactions": []}
        context = self.memory.get_context(limit_traits=0, limit_memories=0, limit_interactions=limit)
        return {"recent_interactions": context.get("recent_interactions", []) or []}

    def _consult_memories(self, limit: int = 5) -> Dict[str, Any]:
        if not self.memory:
            return {"memories": []}
        context = self.memory.get_context(limit_traits=0, limit_memories=limit, limit_interactions=0)
        return {"memories": context.get("memories", []) or []}

    def _search_memory(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Simple keyword search over fetched memories (Phase 1)."""
        if not self.memory or not query:
            return {"query": query, "results": []}

        context = self.memory.get_context(limit_traits=0, limit_memories=50, limit_interactions=0)
        memories = context.get("memories", []) or []
        q = query.lower()
        hits = [m for m in memories if q in (m.get("content", "") or "").lower()]
        return {"query": query, "results": hits[:limit]}

    def _consult_objectives(self) -> Dict[str, Any]:
        if not self.memory:
            return {"objectives": []}
        context = self.memory.get_context(limit_traits=0, limit_memories=0, limit_interactions=0)
        return {"objectives": context.get("session_goals", []) or []}

    def _consult_recent_episodes(self, limit: int = 5) -> Dict[str, Any]:
        if not self.memory:
            return {"recent_episodes": []}
        context = self.memory.get_context(limit_traits=0, limit_memories=limit, limit_interactions=limit)
        episodes: List[Dict[str, Any]] = []
        for it in context.get("recent_interactions", []) or []:
            episodes.append(
                {
                    "type": "interaction",
                    "prompt": it.get("prompt"),
                    "response": it.get("response"),
                    "timestamp": it.get("timestamp"),
                }
            )
        for m in context.get("memories", []) or []:
            episodes.append(
                {
                    "type": "memory",
                    "content": m.get("content"),
                    "category": m.get("category"),
                    "created_at": m.get("created_at"),
                }
            )
        return {"recent_episodes": episodes[:limit]}

    def _search_by_emotion(self, emotion: str, limit: int = 10) -> Dict[str, Any]:
        if not self.memory or not emotion:
            return {"emotion": emotion, "results": []}
        context = self.memory.get_context(limit_traits=0, limit_memories=100, limit_interactions=0)
        memories = context.get("memories", []) or []
        q = emotion.lower()
        hits = []
        for m in memories:
            text = f"{m.get('content', '')} {m.get('category', '')}".lower()
            if q in text:
                hits.append(m)
        return {"emotion": emotion, "results": hits[:limit]}

    async def _query_external(self, query: str) -> Dict[str, Any]:
        if not self.gemini or not query:
            logger.debug(f"      ⚠️  [EXECUTOR] Gemini non disponible ou requête vide")
            return {"query": query, "response": None, "available": False}
        try:
            logger.debug(f"      🔄 [EXECUTOR] Envoi de la requête à Gemini...")
            resp = await self.gemini.query(query, context=None)
            logger.debug(f"      ✅ [EXECUTOR] Réponse Gemini reçue")
            return {"query": query, "response": resp, "available": True}
        except Exception as e:
            logger.error(f"      ❌ [EXECUTOR] Erreur lors de la requête Gemini: {e}")
            return {"query": query, "response": None, "available": False, "error": str(e)}




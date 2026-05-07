"""MemoryBrain V2: façade hiérarchique (MVP).

Objectif: exposer une API stable pour le routeur/dispatcher:
- working memory (état de session)
- long-term memory (via memory_service)
- procedural memory (patterns via PatternLearner)
- architectural memory (ArchitectureGraph changelog)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class WorkingMemory:
    session_id: str
    created_at_iso: str = field(default_factory=lambda: datetime.now().isoformat())
    last_user_message: str = ""
    last_intent: Optional[str] = None
    active_modules: List[str] = field(default_factory=list)
    last_execution_results: Dict[str, Any] = field(default_factory=dict)


class MemoryBrain:
    def __init__(
        self,
        memory_adapter: Any = None,
        pattern_learner: Any = None,
        architecture_graph: Any = None,
    ) -> None:
        self.memory = memory_adapter
        self.pattern_learner = pattern_learner
        self.architecture_graph = architecture_graph
        self._working: Dict[str, WorkingMemory] = {}

    def get_working_memory(self, session_id: str) -> WorkingMemory:
        if session_id not in self._working:
            self._working[session_id] = WorkingMemory(session_id=session_id)
        return self._working[session_id]

    def update_working_memory(
        self,
        session_id: str,
        *,
        last_user_message: Optional[str] = None,
        last_intent: Optional[str] = None,
        active_modules: Optional[List[str]] = None,
        last_execution_results: Optional[Dict[str, Any]] = None,
    ) -> None:
        wm = self.get_working_memory(session_id)
        if isinstance(last_user_message, str):
            wm.last_user_message = last_user_message
        if isinstance(last_intent, str) or last_intent is None:
            wm.last_intent = last_intent
        if isinstance(active_modules, list):
            wm.active_modules = [str(x) for x in active_modules]
        if isinstance(last_execution_results, dict):
            wm.last_execution_results = dict(last_execution_results)

    # --------------------------
    # Long-term memory (store)
    # --------------------------
    def get_long_term_context(
        self,
        *,
        limit_traits: int = 10,
        limit_memories: int = 10,
        limit_interactions: int = 5,
    ) -> Dict[str, Any]:
        if not self.memory:
            return {"traits": [], "memories": [], "recent_interactions": [], "session_goals": []}
        return self.memory.get_context(
            limit_traits=limit_traits,
            limit_memories=limit_memories,
            limit_interactions=limit_interactions,
        )

    # --------------------------
    # Procedural memory (patterns)
    # --------------------------
    def get_preferred_patterns(self, request_type: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.pattern_learner:
            return []
        pats = self.pattern_learner.get_preferred_patterns(request_type=request_type, context=context)
        return [p.to_dict() for p in (pats or [])]

    # --------------------------
    # Architectural memory
    # --------------------------
    def get_architecture_changelog(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.architecture_graph:
            return []
        logs = getattr(self.architecture_graph, "changelog", []) or []
        out = []
        for it in list(logs)[-int(limit) :]:
            out.append(
                {
                    "target_module": getattr(it, "target_module", None),
                    "summary": getattr(it, "summary", None),
                    "author": getattr(it, "author", None),
                    "timestamp_iso": getattr(it, "timestamp_iso", None),
                }
            )
        return out


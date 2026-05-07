"""Core cognitive planning models for LIA.

Phase 1: Provide data structures for planning/execution/verification without
integrating into the runtime generation loop yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    """Types of actions a planner can request."""

    CONSULT_PATTERNS = "consult_patterns"
    CONSULT_REQUEST = "consult_request"
    CONSULT_MEMORY = "consult_memory"
    CONSULT_IDENTITY = "consult_identity"
    CONSULT_TRAITS = "consult_traits"
    CONSULT_ENVIRONMENT = "consult_environment"
    CONSULT_INTERACTIONS = "consult_interactions"
    CONSULT_MEMORIES = "consult_memories"
    CONSULT_OBJECTIVES = "consult_objectives"
    CONSULT_RECENT_EPISODES = "consult_recent_episodes"
    SEARCH_BY_EMOTION = "search_by_emotion"
    SEARCH_MEMORY = "search_memory"
    QUERY_EXTERNAL = "query_external"
    NAVIGATE_GENERAL = "navigate_general"
    NAVIGATE_BASE = "navigate_base"
    RESPOND = "respond"


@dataclass(frozen=True)
class Action:
    """One action step in an ActionPlan."""

    type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    required: bool = True


@dataclass(frozen=True)
class ActionPlan:
    """Ordered list of actions to execute before generating an answer."""

    actions: List[Action]
    estimated_cost: float = 0.0  # heuristic: time/tokens cost
    confidence: float = 0.5  # 0..1
    fallback_plan: Optional["ActionPlan"] = None

    def sorted_actions(self) -> List[Action]:
        return sorted(self.actions, key=lambda a: a.priority)


@dataclass(frozen=True)
class RequestAnalysis:
    """Heuristic analysis of a user request."""

    complexity: str  # "simple" | "moderate" | "complex"
    needs_memory: bool = False
    needs_identity: bool = False
    needs_external: bool = False
    keywords: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionResult:
    """Result of executing an ActionPlan."""

    results: Dict[str, Any] = field(default_factory=dict)  # by ActionType.value
    success: bool = True
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass(frozen=True)
class VerificationResult:
    """Result of verifying a generated response."""

    is_valid: bool
    relevance_score: float = 0.0
    memory_usage_score: float = 0.0
    identity_coherence_score: float = 0.0
    overall_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class Pattern:
    """Pattern d'exécution appris (Phase 3)."""

    id: str
    action_sequence: List[ActionType] = field(default_factory=list)  # Séquence d'actions
    request_types: List[str] = field(default_factory=list)  # Types de requêtes où efficace
    success_rate: float = 0.0  # Taux de succès (0.0 - 1.0)
    avg_quality_score: float = 0.0  # Score de qualité moyen
    avg_execution_time: float = 0.0  # Temps d'exécution moyen
    usage_count: int = 0  # Nombre d'utilisations
    last_used: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le pattern en dictionnaire pour stockage."""
        return {
            "id": self.id,
            "action_sequence": [a.value for a in self.action_sequence],
            "request_types": self.request_types,
            "success_rate": self.success_rate,
            "avg_quality_score": self.avg_quality_score,
            "avg_execution_time": self.avg_execution_time,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pattern":
        """Crée un pattern depuis un dictionnaire."""
        from datetime import datetime
        return cls(
            id=data["id"],
            action_sequence=[ActionType(a) for a in data["action_sequence"]],
            request_types=data.get("request_types", []),
            success_rate=data.get("success_rate", 0.0),
            avg_quality_score=data.get("avg_quality_score", 0.0),
            avg_execution_time=data.get("avg_execution_time", 0.0),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None
        )


class ResponseChunkType(str, Enum):
    """Type de fragment de réponse à exposer à l'interface."""

    PROCESS = "process"   # Étape interne (menu, décision, action exécutée...)
    RESPONSE = "response"  # Sortie utilisateur finale (ou partielle)


@dataclass
class ResponseChunk:
    """Fragment structuré de réponse pour suivi de processus.

    Exemple:
    - type=PROCESS, content="LIA a décidé de consulter sa mémoire."
    - type=RESPONSE, content="Bonjour ! Comment puis-je vous aider aujourd'hui ?"
    """

    type: ResponseChunkType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)




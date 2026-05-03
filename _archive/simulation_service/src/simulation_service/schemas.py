"""Schémas Pydantic pour le service de simulation."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field, field_validator


# Types d'agents
AgentType = Literal["lia-primary", "lia-secondary", "llm-external", "llm-local", "simulated"]
MessageType = Literal["text", "handshake", "error", "system"]
SessionStatus = Literal["running", "stopped", "failed", "completed", "starting"]
GovernanceVerdict = Literal["allow", "warn", "block"]
Capability = Literal["memory", "governance", "multi-turn", "streaming"]


class RateLimitConfig(BaseModel):
    """Configuration de rate limiting."""
    max_messages_per_second: int = Field(default=10, ge=1)
    max_messages_per_minute: int = Field(default=60, ge=1)


class AgentHandshake(BaseModel):
    """Schéma de handshake initial entre agents."""
    agent_id: str
    agent_type: AgentType
    capabilities: List[Capability] = Field(min_length=1)
    memory_version: Optional[str] = Field(None, pattern=r"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[0-9]{2}$")
    api_endpoint: Optional[str] = None
    auth_token: Optional[str] = None
    rate_limit: Optional[RateLimitConfig] = None


class MessageScores(BaseModel):
    """Scores associés à un message."""
    coherence: Optional[float] = Field(None, ge=0.0, le=1.0)
    curiosity: Optional[float] = Field(None, ge=0.0, le=1.0)
    usefulness: Optional[float] = Field(None, ge=0.0, le=1.0)


class MultiAgentMessage(BaseModel):
    """Message échangé entre agents."""
    message_id: str = Field(pattern=r"^msg-[0-9]{8}-[0-9a-f]{3}$")
    session_id: str = Field(pattern=r"^sim-[0-9]{8}-[0-9a-f]{3}$")
    agent_id: str
    agent_partner_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_type: MessageType = "text"
    content: str = Field(min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("message_id", mode="before")
    @classmethod
    def generate_message_id(cls, v: Optional[str]) -> str:
        """Génère un message_id si non fourni."""
        if v is None:
            date_str = datetime.now(UTC).strftime("%Y%m%d")
            return f"msg-{date_str}-{uuid.uuid4().hex[:3]}"
        return v

    @field_validator("session_id", mode="before")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Valide le format du session_id."""
        if not v or not isinstance(v, str):
            raise ValueError("session_id requis")
        return v


class AgentConfig(BaseModel):
    """Configuration d'un agent pour une simulation."""
    agent_id: str
    agent_type: AgentType
    capabilities: List[Capability] = Field(default_factory=list)
    api_endpoint: Optional[str] = None
    auth_token: Optional[str] = None
    memory_service_url: Optional[str] = None  # Pour LIA agents


class SimulationStartRequest(BaseModel):
    """Requête pour démarrer une simulation."""
    agent_configs: List[AgentConfig] = Field(min_length=2, max_length=10)
    scenario: Optional[str] = None
    max_turns: int = Field(default=50, ge=1, le=100)
    timeout_seconds: int = Field(default=30, ge=5, le=300)


class SimulationStartResponse(BaseModel):
    """Réponse au démarrage d'une simulation."""
    session_id: str
    status: Literal["running", "starting"]
    agents: List[str]
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageRequest(BaseModel):
    """Requête pour envoyer un message."""
    agent_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Réponse à l'envoi d'un message."""
    message_id: str
    response_content: str
    response_agent_id: str
    turn: int
    governance_verdict: GovernanceVerdict


class BehavioralMetrics(BaseModel):
    """Métriques comportementales."""
    variability: float = Field(ge=0.0, le=1.0)
    autonomy: float = Field(ge=0.0, le=1.0)
    curiosity: float = Field(ge=0.0, le=1.0)
    coherence: float = Field(ge=0.0, le=1.0)


class SimulationStatus(BaseModel):
    """Statut d'une simulation."""
    session_id: str
    status: SessionStatus
    current_turn: int
    max_turns: int
    messages_count: int
    agents: List[str]
    metrics: Optional[BehavioralMetrics] = None
    started_at: datetime
    last_activity: Optional[datetime] = None


class SimulationStopResponse(BaseModel):
    """Réponse à l'arrêt d'une simulation."""
    session_id: str
    status: SessionStatus
    stopped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    final_metrics: Optional[BehavioralMetrics] = None
    experience_id: Optional[str] = None


class SimulationExport(BaseModel):
    """Export des résultats d'une simulation."""
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    agents: List[str]
    total_turns: int
    metrics: Optional[BehavioralMetrics] = None
    metrics_by_agent: Optional[Dict[str, Dict[str, float]]] = Field(default_factory=dict)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    experiences_created: List[str] = Field(default_factory=list)
    traits_updated: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Réponse d'erreur standard."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

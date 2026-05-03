"""Schémas Pydantic du service mémoire."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field, validator


MemoryCategory = Literal["fact", "preference", "alert"]


class Trait(BaseModel):
    trait_id: str
    type: str
    label: str
    value: str
    version: int = 1
    weight: float = 1.0
    confidence: float = 0.8
    last_update: datetime = Field(default_factory=lambda: datetime.now(UTC))
    origin: str = "system"
    status: Literal["active", "staged", "deprecated"] = "active"


class TraitUpdateRequest(BaseModel):
    trait_id: str
    delta: Dict[str, Any]  # Objet au lieu de string
    reason: str
    source: str
    expected_version: Optional[int] = None


class TraitUpdateResponse(BaseModel):
    trait: Trait
    version_token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    review_required: bool = False


class LinkRef(BaseModel):
    type: Literal["trait", "experience", "interaction"]
    id: str


class Souvenir(BaseModel):
    memory_id: str
    category: MemoryCategory
    content: str
    tags: Sequence[str] = Field(default_factory=list)
    importance_score: float = 0.5
    recency_score: float = 0.5
    emotion_score: float = 0.0
    frequency: int = 1  # Ajout du champ frequency
    ttl: datetime  # Changé de int à datetime
    source: str = "interaction"
    link_refs: Sequence[LinkRef] = Field(default_factory=list)
    hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @validator("importance_score", "recency_score", "emotion_score")
    def clamp_scores(cls, value: float) -> float:
        return max(0.0, min(1.0, value))


class SessionGoal(BaseModel):
    goal_id: str
    session_id: str
    priority: float = 0.5
    description: str
    blocking_conditions: Sequence[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class Indicator(BaseModel):
    indicator_id: str
    type: str
    value: float
    window: int
    status: Literal["ok", "warn", "alert"] = "ok"
    thresholds: Dict[str, float] = Field(default_factory=dict)
    history: Sequence[float] = Field(default_factory=list)


class InteractionScores(BaseModel):
    usefulness: float = 0.8
    coherence: float = 0.9
    tone: float = 0.9


class InteractionEmotions(BaseModel):
    valence: float = 0.0
    arousal: float = 0.0


class InteractionDecisions(BaseModel):
    create_memory: bool = True
    ttl_override_days: Optional[int] = None
    derived_traits: Sequence[str] = Field(default_factory=list)


class InteractionRequest(BaseModel):
    interaction_id: str
    session_id: str
    prompt: str
    response: str
    scores: InteractionScores = Field(default_factory=InteractionScores)
    emotions: Optional[InteractionEmotions] = None
    decisions: InteractionDecisions = Field(default_factory=InteractionDecisions)
    anomalies: Sequence[str] = Field(default_factory=list)


class InteractionLog(BaseModel):
    interaction_id: str
    session_id: str
    occurred_at: datetime  # Renommé de timestamp
    prompt: str
    response: str
    scores: Dict[str, Any]  # JSON
    derived_traits: Sequence[str]
    anomalies: Sequence[str]
    severity: Literal["info", "warning", "error"] = "info"
    raw_size_bytes: Optional[int] = None


class ContextResponse(BaseModel):
    traits: List[Trait]
    session_goals: List[SessionGoal]
    memories: List[Souvenir]
    indicators: Dict[str, float]
    governance_metadata: Dict[str, str]
    build_time_ms: int
    trace_id: str
    cache_hit: bool = False
    context_checksum: str


class GovernanceSignal(BaseModel):
    type: str
    value: float
    metadata: Optional[Dict[str, Any]] = None


class GovernanceCheckRequest(BaseModel):
    session_id: str
    draft_response: str
    signals: Sequence[GovernanceSignal] = Field(default_factory=list)


class GovernanceIssue(BaseModel):
    code: str  # Renommé de type
    severity: Literal["info", "warning", "error"] = "warning"
    message: str
    value: Optional[float] = None


class AutoFix(BaseModel):
    action: str
    payload: Optional[Dict[str, Any]] = None


class GovernanceCheckResponse(BaseModel):
    verdict: Literal["allow", "warn", "block"]
    issues: List[GovernanceIssue]
    auto_fix: Optional[AutoFix] = None


class MetricSnapshot(BaseModel):
    latency_context_ms: float = 0.0
    context_payload_bytes: int = 0
    coverage_traits_pct: float = 1.0
    coherence_score: float = 0.9
    drift_alerts_count: int = 0
    ttl_purge_rate: float = 0.0
    store_availability: float = 1.0


class MetricsResponse(BaseModel):
    indicators: Dict[str, float]
    kpis: MetricSnapshot  # Renommé de kpi à kpis pour correspondre à l'OpenAPI
    window: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Schémas pour Personal Goals (Étape 2.6)
class PersonalGoal(BaseModel):
    """Objectif personnel de LIA."""
    goal_id: str
    goal_type: Literal["research", "hobby", "task"]
    description: str
    priority: float = Field(ge=0.0, le=1.0)  # 0.0 - 1.0
    status: Literal["active", "paused", "completed", "archived"]
    trigger_conditions: Optional[Dict[str, Any]] = None
    frequency: Literal["once", "daily", "weekly", "monthly"]
    created_at: datetime
    last_triggered_at: Optional[datetime] = None
    next_trigger_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class PersonalGoalCreate(BaseModel):
    """Requête de création d'objectif personnel."""
    goal_type: Literal["research", "hobby", "task"]
    description: str
    priority: float = Field(ge=0.0, le=1.0, default=0.5)
    trigger_conditions: Optional[Dict[str, Any]] = None
    frequency: Literal["once", "daily", "weekly", "monthly"] = "once"
    metadata: Optional[Dict[str, Any]] = None


class PersonalGoalUpdate(BaseModel):
    """Requête de mise à jour d'objectif personnel."""
    description: Optional[str] = None
    priority: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[Literal["active", "paused", "completed", "archived"]] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    frequency: Optional[Literal["once", "daily", "weekly", "monthly"]] = None
    next_trigger_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

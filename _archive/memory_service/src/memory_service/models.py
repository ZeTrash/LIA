"""Modèles SQLAlchemy pour la mémoire persistante."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TraitModel(Base):
    __tablename__ = "traits"

    trait_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # Enum: persona, skill, style, constraint
    label: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    origin: Mapped[str] = mapped_column(String, default="system")
    status: Mapped[str] = mapped_column(String, default="active")  # Enum: active, staged, deprecated
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)  # SHA3-256

    versions: Mapped[list["TraitVersionModel"]] = relationship(
        back_populates="trait",
        cascade="all, delete-orphan",
        order_by="TraitVersionModel.version.desc()",
    )


class TraitVersionModel(Base):
    __tablename__ = "trait_versions"

    trait_id: Mapped[str] = mapped_column(String, ForeignKey("traits.trait_id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    delta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String, nullable=True)

    trait: Mapped[TraitModel] = relationship(back_populates="versions")


class SouvenirModel(Base):
    __tablename__ = "souvenirs"

    memory_id: Mapped[str] = mapped_column(String, primary_key=True)
    category: Mapped[str] = mapped_column(String, nullable=False)  # Enum: fact, preference, alert
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # Stockage texte
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    recency_score: Mapped[float] = mapped_column(Float, default=0.5)
    emotion_score: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ttl: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Changé en datetime
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    hash: Mapped[str] = mapped_column(String, nullable=False)  # SHA3-256, non nullable
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)  # Renommé de last_seen_at

    links: Mapped[list["SouvenirLinkModel"]] = relationship(
        back_populates="souvenir",
        cascade="all, delete-orphan",
    )


class SouvenirLinkModel(Base):
    __tablename__ = "souvenir_links"

    memory_id: Mapped[str] = mapped_column(String, ForeignKey("souvenirs.memory_id"), primary_key=True)
    target_type: Mapped[str] = mapped_column(String, primary_key=True)  # Enum: trait, experience, interaction
    target_id: Mapped[str] = mapped_column(String, primary_key=True)

    souvenir: Mapped[SouvenirModel] = relationship(back_populates="links")


class InteractionModel(Base):
    __tablename__ = "interaction_logs"  # Renommé de interactions

    interaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)  # Renommé de timestamp
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    derived_traits: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    anomalies: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(String, default="info", nullable=False)  # Enum: info, warning, error
    raw_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SessionGoalModel(Base):
    __tablename__ = "session_goals"

    goal_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    blocking_conditions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Non nullable
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)  # Enum: active, snoozed, done


class ExperienceModel(Base):
    __tablename__ = "experiences"

    experience_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    period: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    related_memories: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class IndicatorModel(Base):
    __tablename__ = "indicators"

    indicator_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    window: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # Enum: ok, warn, alert
    thresholds: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    history: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class GovernanceParamModel(Base):
    __tablename__ = "governance_params"

    param_id: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    default_value: Mapped[str] = mapped_column(String, nullable=False)
    min_value: Mapped[str | None] = mapped_column(String, nullable=True)
    max_value: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    param_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class RequestAuditModel(Base):
    __tablename__ = "request_audit"

    audit_id: Mapped[str] = mapped_column(String, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    context_version: Mapped[str | None] = mapped_column(String, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class PersonalGoalModel(Base):
    __tablename__ = "personal_goals"

    goal_id: Mapped[str] = mapped_column(String, primary_key=True)
    goal_type: Mapped[str] = mapped_column(String, nullable=False)  # Enum: research, hobby, task
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0
    status: Mapped[str] = mapped_column(String, nullable=False)  # Enum: active, paused, completed, archived
    trigger_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    frequency: Mapped[str] = mapped_column(String, nullable=False)  # Enum: once, daily, weekly, monthly
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_trigger_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint("goal_type IN ('research', 'hobby', 'task')", name="check_goal_type"),
        CheckConstraint("priority BETWEEN 0 AND 1", name="check_priority"),
        CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')", name="check_status"),
        CheckConstraint("frequency IN ('once', 'daily', 'weekly', 'monthly')", name="check_frequency"),
    )

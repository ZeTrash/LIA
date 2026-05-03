"""Modèles SQLAlchemy pour la mémoire persistante."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Any
import uuid

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TraitModel(Base):
    """Modèle pour les traits de personnalité."""
    __tablename__ = "traits"

    trait_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # persona, skill, style, constraint
    label: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")  # active, staged, deprecated


class SouvenirModel(Base):
    """Modèle pour les souvenirs/mémoires."""
    __tablename__ = "souvenirs"

    memory_id: Mapped[str] = mapped_column(String, primary_key=True)
    category: Mapped[str] = mapped_column(String, nullable=False)  # fact, preference, alert
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    recency_score: Mapped[float] = mapped_column(Float, default=0.5)
    emotion_score: Mapped[float] = mapped_column(Float, default=0.0)
    memory_rank_score: Mapped[float] = mapped_column(Float, default=0.0)  # Score MemoryRank (PageRank)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ttl: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class InteractionModel(Base):
    """Modèle pour les logs d'interactions."""
    __tablename__ = "interaction_logs"

    interaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(String, default="info", nullable=False)  # info, warning, error


class ThemePatternModel(Base):
    """Modèle pour les thèmes de patterns (V2).

    Chaque thème représente une catégorie de requêtes (ex: salutation, mémoire, identité).
    """

    __tablename__ = "theme_patterns"

    theme_id: Mapped[str] = mapped_column(String, primary_key=True)
    theme_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class PatternModel(Base):
    """Modèle pour les patterns (recommandations) utilisés dans les menus.

    Version de départ (seed/fake patterns) : permet d'observer l'inclusion des recommandations
    dans les prompts de menu avant de brancher Gemini.

    V2 : theme_pattern optionnel pour filtrer les recommandations par thème.
    """

    __tablename__ = "patterns"

    pattern_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Thème associé (V2, nullable pour rétrocompatibilité)
    theme_pattern: Mapped[str | None] = mapped_column(String, nullable=True)

    # Contexte: "base" ou "general" (ou autres sous-menus plus tard)
    menu_context: Mapped[str] = mapped_column(String, nullable=False)

    # Étape précédente (ex: "initial", "B2", "G1"...)
    prev_step: Mapped[str] = mapped_column(String, nullable=False)

    # Étape recommandée (ex: "B2", "G4"...)
    recommended_step: Mapped[str] = mapped_column(String, nullable=False)

    # Poids par step (somme = 1.0 idéalement)
    weights: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Métadonnées (source, notes, versioning simple)
    source: Mapped[str] = mapped_column(String, default="seed", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class MemoryLinkModel(Base):
    """Modèle pour les liens entre souvenirs (graphe de mémoire MemoryRank).
    
    Représente une référence d'un souvenir source vers un souvenir cible,
    avec un poids indiquant la force de la référence.
    """
    __tablename__ = "memory_links"

    link_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_memory_id: Mapped[str] = mapped_column(String, ForeignKey("souvenirs.memory_id"), nullable=False)
    target_memory_id: Mapped[str] = mapped_column(String, ForeignKey("souvenirs.memory_id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # Force de référence (wij)
    link_type: Mapped[str] = mapped_column(String, nullable=False)  # cooccurrence, similarity, citation, causal, etc.
    link_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Métadonnées additionnelles
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


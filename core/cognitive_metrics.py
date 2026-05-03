"""CognitiveMetrics: système de monitoring et métriques (Phase 5)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Métriques pour une exécution."""

    session_id: str
    timestamp: datetime
    planning_time: float = 0.0
    execution_time: float = 0.0
    total_time: float = 0.0
    tokens_used: int = 0
    actions_count: int = 0
    memory_accesses: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    plan_confidence: float = 0.0
    verification_score: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)


class CognitiveMetrics:
    """Collecteur de métriques pour le système cognitif."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le collecteur de métriques.

        Args:
            config: Configuration
        """
        self.config = config or {}
        self.metrics: List[ExecutionMetrics] = []
        self.session_metrics: Dict[str, List[ExecutionMetrics]] = defaultdict(list)
        self.max_metrics_history = self.config.get("max_metrics_history", 1000)

        logger.info("CognitiveMetrics initialisé")

    def record_execution(
        self,
        session_id: str,
        planning_time: float = 0.0,
        execution_time: float = 0.0,
        total_time: float = 0.0,
        tokens_used: int = 0,
        actions_count: int = 0,
        memory_accesses: int = 0,
        cache_hits: int = 0,
        cache_misses: int = 0,
        plan_confidence: float = 0.0,
        verification_score: float = 0.0,
        success: bool = True,
        errors: Optional[List[str]] = None,
    ) -> None:
        """
        Enregistre les métriques d'une exécution.

        Args:
            session_id: ID de session
            planning_time: Temps de planification (secondes)
            execution_time: Temps d'exécution (secondes)
            total_time: Temps total (secondes)
            tokens_used: Nombre de tokens utilisés
            actions_count: Nombre d'actions exécutées
            memory_accesses: Nombre d'accès mémoire
            cache_hits: Nombre de hits de cache
            cache_misses: Nombre de misses de cache
            plan_confidence: Confiance dans le plan (0.0-1.0)
            verification_score: Score de vérification (0.0-1.0)
            success: Succès de l'exécution
            errors: Liste d'erreurs (optionnel)
        """
        metric = ExecutionMetrics(
            session_id=session_id,
            timestamp=datetime.now(UTC),
            planning_time=planning_time,
            execution_time=execution_time,
            total_time=total_time,
            tokens_used=tokens_used,
            actions_count=actions_count,
            memory_accesses=memory_accesses,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            plan_confidence=plan_confidence,
            verification_score=verification_score,
            success=success,
            errors=errors or [],
        )

        self.metrics.append(metric)
        self.session_metrics[session_id].append(metric)

        # Limiter l'historique
        if len(self.metrics) > self.max_metrics_history:
            self.metrics = self.metrics[-self.max_metrics_history:]

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Retourne les statistiques pour une session.

        Args:
            session_id: ID de session

        Returns:
            Dictionnaire avec les statistiques
        """
        session_metrics = self.session_metrics.get(session_id, [])

        if not session_metrics:
            return {
                "session_id": session_id,
                "execution_count": 0,
                "avg_total_time": 0.0,
                "avg_planning_time": 0.0,
                "avg_execution_time": 0.0,
                "success_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_verification_score": 0.0,
            }

        execution_count = len(session_metrics)
        successful = sum(1 for m in session_metrics if m.success)

        return {
            "session_id": session_id,
            "execution_count": execution_count,
            "avg_total_time": sum(m.total_time for m in session_metrics) / execution_count,
            "avg_planning_time": sum(m.planning_time for m in session_metrics) / execution_count,
            "avg_execution_time": sum(m.execution_time for m in session_metrics) / execution_count,
            "success_rate": successful / execution_count if execution_count > 0 else 0.0,
            "avg_confidence": sum(m.plan_confidence for m in session_metrics) / execution_count,
            "avg_verification_score": sum(m.verification_score for m in session_metrics) / execution_count,
            "total_tokens": sum(m.tokens_used for m in session_metrics),
            "total_memory_accesses": sum(m.memory_accesses for m in session_metrics),
            "cache_hit_rate": (
                sum(m.cache_hits for m in session_metrics)
                / (sum(m.cache_hits + m.cache_misses for m in session_metrics) or 1)
                * 100
            ),
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques globales.

        Returns:
            Dictionnaire avec les statistiques globales
        """
        if not self.metrics:
            return {
                "total_executions": 0,
                "avg_total_time": 0.0,
                "success_rate": 0.0,
            }

        total_executions = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)

        return {
            "total_executions": total_executions,
            "avg_total_time": sum(m.total_time for m in self.metrics) / total_executions,
            "avg_planning_time": sum(m.planning_time for m in self.metrics) / total_executions,
            "avg_execution_time": sum(m.execution_time for m in self.metrics) / total_executions,
            "success_rate": successful / total_executions,
            "avg_confidence": sum(m.plan_confidence for m in self.metrics) / total_executions,
            "avg_verification_score": sum(m.verification_score for m in self.metrics) / total_executions,
            "total_tokens": sum(m.tokens_used for m in self.metrics),
            "total_memory_accesses": sum(m.memory_accesses for m in self.metrics),
            "cache_hit_rate": (
                sum(m.cache_hits for m in self.metrics)
                / (sum(m.cache_hits + m.cache_misses for m in self.metrics) or 1)
                * 100
            ),
            "unique_sessions": len(self.session_metrics),
        }

    def get_recent_metrics(self, limit: int = 10) -> List[ExecutionMetrics]:
        """
        Retourne les métriques les plus récentes.

        Args:
            limit: Nombre de métriques à retourner

        Returns:
            Liste des métriques les plus récentes
        """
        return self.metrics[-limit:]

    def clear_metrics(self) -> None:
        """Efface toutes les métriques."""
        self.metrics.clear()
        self.session_metrics.clear()
        logger.info("Métriques effacées")


"""Tests pour CognitiveMetrics (Phase 5)."""

import pytest
from core.cognitive_metrics import CognitiveMetrics, ExecutionMetrics


@pytest.fixture
def metrics():
    """Crée un CognitiveMetrics pour tests."""
    config = {"max_metrics_history": 100}
    return CognitiveMetrics(config=config)


def test_record_execution(metrics):
    """Test enregistrement d'une exécution."""
    metrics.record_execution(
        session_id="session1",
        planning_time=0.1,
        execution_time=0.5,
        total_time=0.6,
        tokens_used=100,
        actions_count=3,
        memory_accesses=2,
        cache_hits=1,
        cache_misses=0,
        plan_confidence=0.8,
        verification_score=0.9,
        success=True
    )
    
    assert len(metrics.metrics) == 1
    assert metrics.metrics[0].session_id == "session1"
    assert metrics.metrics[0].planning_time == 0.1


def test_get_session_stats(metrics):
    """Test récupération statistiques session."""
    # Enregistrer plusieurs exécutions
    for i in range(3):
        metrics.record_execution(
            session_id="session1",
            planning_time=0.1 * (i + 1),
            execution_time=0.5,
            total_time=0.6,
            success=True,
            plan_confidence=0.8
        )
    
    stats = metrics.get_session_stats("session1")
    
    assert stats["session_id"] == "session1"
    assert stats["execution_count"] == 3
    assert stats["success_rate"] == 1.0
    assert abs(stats["avg_confidence"] - 0.8) < 0.01  # Tolérance pour arrondi


def test_get_global_stats(metrics):
    """Test récupération statistiques globales."""
    # Enregistrer plusieurs exécutions
    for i in range(5):
        metrics.record_execution(
            session_id=f"session{i % 2}",  # 2 sessions différentes
            planning_time=0.1,
            execution_time=0.5,
            total_time=0.6,
            success=(i % 2 == 0),  # Alterner succès/échec
            plan_confidence=0.8
        )
    
    stats = metrics.get_global_stats()
    
    assert stats["total_executions"] == 5
    assert stats["unique_sessions"] == 2
    assert 0.0 <= stats["success_rate"] <= 1.0


def test_get_recent_metrics(metrics):
    """Test récupération métriques récentes."""
    # Enregistrer plusieurs exécutions
    for i in range(10):
        metrics.record_execution(
            session_id="session1",
            planning_time=0.1,
            execution_time=0.5,
            total_time=0.6
        )
    
    recent = metrics.get_recent_metrics(limit=5)
    
    assert len(recent) == 5
    # Les plus récentes devraient être les dernières
    assert recent[-1].timestamp >= recent[0].timestamp


def test_clear_metrics(metrics):
    """Test effacement métriques."""
    # Enregistrer quelques métriques
    for i in range(5):
        metrics.record_execution(
            session_id="session1",
            planning_time=0.1,
            execution_time=0.5,
            total_time=0.6
        )
    
    assert len(metrics.metrics) == 5
    
    metrics.clear_metrics()
    
    assert len(metrics.metrics) == 0
    assert len(metrics.session_metrics) == 0


def test_max_metrics_history(metrics):
    """Test limite historique métriques."""
    # Enregistrer plus que max_metrics_history
    for i in range(150):  # Plus que max_metrics_history (100)
        metrics.record_execution(
            session_id="session1",
            planning_time=0.1,
            execution_time=0.5,
            total_time=0.6
        )
    
    # Devrait être limité à max_metrics_history
    assert len(metrics.metrics) <= metrics.max_metrics_history


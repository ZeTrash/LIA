"""Tests pour CognitiveOptimizer (Phase 5)."""

import pytest
import time
from core.cognitive_optimizer import CognitiveOptimizer, DecisionCache
from core.cognitive_models import ActionPlan, Action, ActionType, RequestAnalysis


@pytest.fixture
def optimizer():
    """Crée un CognitiveOptimizer pour tests."""
    config = {
        "enable_cache": True,
        "cache_size": 10,
        "cache_ttl_seconds": 3600.0,
        "enable_parallelization": True,
        "enable_prompt_optimization": True
    }
    return CognitiveOptimizer(config=config)


@pytest.fixture
def sample_plan():
    """Crée un plan d'exemple."""
    return ActionPlan(
        actions=[
            Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2)
        ],
        estimated_cost=50.0,
        confidence=0.8
    )


@pytest.fixture
def sample_analysis():
    """Crée une analyse d'exemple."""
    return RequestAnalysis(
        complexity="simple",
        needs_identity=True,
        needs_memory=False,
        needs_external=False,
        keywords=["test"]
    )


def test_cache_get_miss(optimizer, sample_plan, sample_analysis):
    """Test récupération depuis cache (miss)."""
    cached = optimizer.get_cached_plan("test message", sample_analysis)
    assert cached is None


def test_cache_put_and_get(optimizer, sample_plan, sample_analysis):
    """Test mise en cache et récupération."""
    message = "test message"
    
    # Mettre en cache
    optimizer.cache_plan(message, sample_analysis, sample_plan)
    
    # Récupérer
    cached = optimizer.get_cached_plan(message, sample_analysis)
    assert cached is not None
    assert len(cached.actions) == len(sample_plan.actions)


def test_cache_expiration(optimizer, sample_plan, sample_analysis):
    """Test expiration du cache."""
    # Créer un cache avec TTL très court
    cache = DecisionCache(max_size=10, ttl_seconds=0.1)
    optimizer.decision_cache = cache
    
    message = "test message"
    optimizer.cache_plan(message, sample_analysis, sample_plan)
    
    # Attendre expiration
    time.sleep(0.2)
    
    # Devrait être expiré
    cached = optimizer.get_cached_plan(message, sample_analysis)
    assert cached is None


def test_cache_lru_eviction(optimizer, sample_plan, sample_analysis):
    """Test éviction LRU du cache."""
    # Créer un cache de taille 2
    cache = DecisionCache(max_size=2, ttl_seconds=3600.0)
    optimizer.decision_cache = cache
    
    # Ajouter 3 plans
    optimizer.cache_plan("message1", sample_analysis, sample_plan)
    optimizer.cache_plan("message2", sample_analysis, sample_plan)
    optimizer.cache_plan("message3", sample_analysis, sample_plan)
    
    # Le premier devrait être évincé
    cached1 = optimizer.get_cached_plan("message1", sample_analysis)
    assert cached1 is None
    
    # Les deux autres devraient être présents
    cached2 = optimizer.get_cached_plan("message2", sample_analysis)
    cached3 = optimizer.get_cached_plan("message3", sample_analysis)
    assert cached2 is not None
    assert cached3 is not None


def test_identify_parallelizable_actions(optimizer, sample_plan):
    """Test identification actions parallélisables."""
    groups = optimizer.identify_parallelizable_actions(sample_plan)
    
    assert len(groups) > 0
    assert all(isinstance(group, list) for group in groups)


def test_optimize_prompt_short(optimizer):
    """Test optimisation prompt court."""
    prompt = "Short prompt"
    optimized = optimizer.optimize_prompt(prompt, max_length=100)
    assert optimized == prompt


def test_optimize_prompt_long(optimizer):
    """Test optimisation prompt long."""
    prompt = "A" * 200
    optimized = optimizer.optimize_prompt(prompt, max_length=100)
    assert len(optimized) <= 100


def test_get_optimization_stats(optimizer):
    """Test récupération statistiques optimisation."""
    stats = optimizer.get_optimization_stats()
    
    assert "cache" in stats
    assert "parallelization_enabled" in stats
    assert "prompt_optimization_enabled" in stats
    assert stats["cache"]["size"] >= 0


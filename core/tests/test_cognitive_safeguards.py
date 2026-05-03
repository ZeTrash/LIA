"""Tests pour CognitiveSafeguards (Phase 5)."""

import pytest
from core.cognitive_safeguards import CognitiveSafeguards, SafeguardConfig, ReflectionBudget
from core.cognitive_models import ActionPlan, Action, ActionType


@pytest.fixture
def safeguard_config():
    """Crée une configuration de garde-fous pour tests."""
    return SafeguardConfig(
        max_decision_depth=3,
        max_reflection_tokens=500,
        max_reflection_time=2.0,
        max_memory_access_cost=100.0,
        max_actions_per_plan=10,
        enable_loop_detection=True,
        max_loop_iterations=3
    )


@pytest.fixture
def safeguards(safeguard_config):
    """Crée un CognitiveSafeguards pour tests."""
    return CognitiveSafeguards(config=safeguard_config)


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
def large_plan():
    """Crée un plan avec beaucoup d'actions."""
    actions = [
        Action(ActionType.CONSULT_IDENTITY, {}, priority=i)
        for i in range(15)  # Plus que max_actions_per_plan (10)
    ]
    return ActionPlan(actions=actions, estimated_cost=200.0, confidence=0.5)


def test_check_decision_depth_ok(safeguards):
    """Test vérification profondeur OK."""
    assert safeguards.check_decision_depth("session1", 2) is True


def test_check_decision_depth_exceeded(safeguards):
    """Test vérification profondeur dépassée."""
    assert safeguards.check_decision_depth("session1", 5) is False


def test_check_reflection_budget_ok(safeguards):
    """Test vérification budget réflexion OK."""
    assert safeguards.check_reflection_budget("session1", tokens=100, time_elapsed=0.5) is True


def test_check_reflection_budget_tokens_exceeded(safeguards):
    """Test budget tokens dépassé."""
    assert safeguards.check_reflection_budget("session1", tokens=600, time_elapsed=0.1) is False


def test_check_reflection_budget_time_exceeded(safeguards):
    """Test budget temps dépassé."""
    assert safeguards.check_reflection_budget("session1", tokens=100, time_elapsed=3.0) is False


def test_check_memory_cost_ok(safeguards):
    """Test vérification coût mémoire OK."""
    assert safeguards.check_memory_cost("session1", cost=50.0) is True


def test_check_memory_cost_exceeded(safeguards):
    """Test coût mémoire dépassé."""
    assert safeguards.check_memory_cost("session1", cost=150.0) is False


def test_check_action_limit_ok(safeguards, sample_plan):
    """Test vérification limite d'actions OK."""
    assert safeguards.check_action_limit(sample_plan) is True


def test_check_action_limit_exceeded(safeguards, large_plan):
    """Test limite d'actions dépassée."""
    assert safeguards.check_action_limit(large_plan) is False


def test_detect_cognitive_loop(safeguards, sample_plan):
    """Test détection de boucle cognitive."""
    session_id = "session1"
    
    # Première utilisation: pas de boucle
    assert safeguards.detect_cognitive_loop(session_id, sample_plan) is False
    
    # Répéter plusieurs fois
    for _ in range(3):
        safeguards.detect_cognitive_loop(session_id, sample_plan)
    
    # Maintenant devrait détecter une boucle
    assert safeguards.detect_cognitive_loop(session_id, sample_plan) is True


def test_validate_plan_ok(safeguards, sample_plan):
    """Test validation plan OK."""
    is_valid, issues = safeguards.validate_plan("session1", sample_plan, current_depth=1)
    assert is_valid is True
    assert len(issues) == 0


def test_validate_plan_invalid_depth(safeguards, sample_plan):
    """Test validation plan avec profondeur excessive."""
    is_valid, issues = safeguards.validate_plan("session1", sample_plan, current_depth=5)
    assert is_valid is False
    assert len(issues) > 0


def test_validate_plan_invalid_actions(safeguards, large_plan):
    """Test validation plan avec trop d'actions."""
    is_valid, issues = safeguards.validate_plan("session1", large_plan, current_depth=1)
    assert is_valid is False
    assert any("actions" in issue.lower() for issue in issues)


def test_record_reflection_usage(safeguards):
    """Test enregistrement utilisation ressources."""
    session_id = "session1"
    
    safeguards.record_reflection_usage(
        session_id=session_id,
        tokens=100,
        time_elapsed=0.5,
        memory_cost=20.0
    )
    
    budget = safeguards.get_budget(session_id)
    assert budget.tokens_used == 100
    assert budget.time_used == 0.5
    assert budget.memory_cost == 20.0
    assert budget.depth == 1


def test_reset_budget(safeguards):
    """Test réinitialisation budget."""
    session_id = "session1"
    
    safeguards.record_reflection_usage(session_id, tokens=100, time_elapsed=0.5)
    safeguards.reset_budget(session_id)
    
    budget = safeguards.get_budget(session_id)
    assert budget.tokens_used == 0
    assert budget.time_used == 0.0


def test_get_budget_status(safeguards):
    """Test récupération statut budget."""
    session_id = "session1"
    
    safeguards.record_reflection_usage(
        session_id=session_id,
        tokens=200,
        time_elapsed=1.0,
        memory_cost=50.0
    )
    
    status = safeguards.get_budget_status(session_id)
    assert status["tokens_used"] == 200
    assert status["tokens_remaining"] == 300  # 500 - 200
    assert status["time_used"] == 1.0
    assert status["time_remaining"] == 1.0  # 2.0 - 1.0
    assert status["memory_cost"] == 50.0
    assert status["depth"] == 1


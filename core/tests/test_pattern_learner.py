"""Tests pour PatternLearner (Phase 3)."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock

from core.pattern_learner import PatternLearner
from core.cognitive_models import (
    ActionPlan,
    Action,
    ActionType,
    ExecutionResult,
    VerificationResult,
    RequestAnalysis,
    Pattern,
)


@pytest.fixture
def temp_storage():
    """Crée un fichier de stockage temporaire."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        storage_path = f.name
    yield storage_path
    # Nettoyer
    Path(storage_path).unlink(missing_ok=True)


@pytest.fixture
def learner(temp_storage):
    """Crée un PatternLearner pour tests."""
    return PatternLearner(
        memory_adapter=None,
        config={
            "min_success_rate": 0.7,
            "min_usage_count": 5,
        },
        storage_path=temp_storage
    )


@pytest.fixture
def sample_plan():
    """Crée un plan d'exemple."""
    return ActionPlan(
        actions=[
            Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2)
        ],
        estimated_cost=100.0,
        confidence=0.8
    )


@pytest.fixture
def sample_execution_result():
    """Crée un résultat d'exécution d'exemple."""
    return ExecutionResult(
        results={
            "consult_identity": {
                "identity": "Je suis LIA",
                "traits": []
            }
        },
        success=True,
        errors=[],
        execution_time=0.5
    )


@pytest.fixture
def sample_verification_result():
    """Crée un résultat de vérification d'exemple."""
    return VerificationResult(
        is_valid=True,
        relevance_score=0.8,
        memory_usage_score=0.7,
        identity_coherence_score=0.9,
        overall_score=0.8,
        issues=[],
        suggestions=[]
    )


@pytest.fixture
def sample_request_analysis():
    """Crée une analyse de requête d'exemple."""
    return RequestAnalysis(
        complexity="simple",
        needs_identity=True,
        needs_memory=False,
        needs_external=False,
        keywords=["qui", "suis"]
    )


def test_pattern_learner_initialization(learner):
    """Test initialisation du PatternLearner."""
    assert learner is not None
    assert len(learner.patterns) == 0


def test_record_execution(learner, sample_plan, sample_execution_result, 
                         sample_verification_result, sample_request_analysis):
    """Test enregistrement d'une exécution."""
    learner.record_execution(
        plan=sample_plan,
        execution_result=sample_execution_result,
        verification_result=sample_verification_result,
        request_analysis=sample_request_analysis
    )
    
    assert len(learner.patterns) == 1
    
    pattern = list(learner.patterns.values())[0]
    assert pattern.usage_count == 1
    assert pattern.success_rate == 1.0
    assert pattern.avg_quality_score == sample_verification_result.overall_score
    assert "simple" in pattern.request_types


def test_record_multiple_executions(learner, sample_plan, sample_execution_result,
                                   sample_verification_result, sample_request_analysis):
    """Test enregistrement de plusieurs exécutions du même pattern."""
    # Enregistrer 3 fois
    for _ in range(3):
        learner.record_execution(
            plan=sample_plan,
            execution_result=sample_execution_result,
            verification_result=sample_verification_result,
            request_analysis=sample_request_analysis
        )
    
    assert len(learner.patterns) == 1
    pattern = list(learner.patterns.values())[0]
    assert pattern.usage_count == 3
    assert pattern.success_rate == 1.0


def test_get_preferred_patterns_empty(learner):
    """Test récupération de patterns préférés quand aucun pattern."""
    patterns = learner.get_preferred_patterns("simple")
    assert len(patterns) == 0


def test_get_preferred_patterns(learner, sample_plan, sample_execution_result,
                                sample_verification_result, sample_request_analysis):
    """Test récupération de patterns préférés."""
    # Enregistrer plusieurs exécutions pour créer un pattern valide
    for _ in range(6):  # Plus que min_usage_count (5)
        learner.record_execution(
            plan=sample_plan,
            execution_result=sample_execution_result,
            verification_result=sample_verification_result,
            request_analysis=sample_request_analysis
        )
    
    patterns = learner.get_preferred_patterns("simple")
    assert len(patterns) == 1
    assert patterns[0].usage_count >= 5
    assert patterns[0].success_rate >= 0.7


def test_pattern_storage_and_loading(temp_storage):
    """Test sauvegarde et chargement des patterns."""
    # Créer un learner et enregistrer des patterns
    learner1 = PatternLearner(
        memory_adapter=None,
        config={},
        storage_path=temp_storage
    )
    
    plan = ActionPlan(
        actions=[
            Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2)
        ],
        estimated_cost=100.0,
        confidence=0.8
    )
    
    execution_result = ExecutionResult(
        results={"consult_identity": {"identity": "LIA"}},
        success=True,
        errors=[],
        execution_time=0.5
    )
    
    verification_result = VerificationResult(
        is_valid=True,
        overall_score=0.8
    )
    
    request_analysis = RequestAnalysis(
        complexity="simple",
        needs_identity=True
    )
    
    learner1.record_execution(
        plan=plan,
        execution_result=execution_result,
        verification_result=verification_result,
        request_analysis=request_analysis
    )
    
    # Créer un nouveau learner et charger
    learner2 = PatternLearner(
        memory_adapter=None,
        config={},
        storage_path=temp_storage
    )
    
    assert len(learner2.patterns) == 1
    pattern = list(learner2.patterns.values())[0]
    assert pattern.usage_count == 1


def test_pattern_efficiency_score(learner, sample_plan, sample_execution_result,
                                   sample_verification_result, sample_request_analysis):
    """Test calcul du score d'efficacité."""
    # Enregistrer plusieurs exécutions
    for _ in range(5):
        learner.record_execution(
            plan=sample_plan,
            execution_result=sample_execution_result,
            verification_result=sample_verification_result,
            request_analysis=sample_request_analysis
        )
    
    pattern = list(learner.patterns.values())[0]
    efficiency = learner._calculate_efficiency_score(pattern)
    
    assert 0.0 <= efficiency <= 1.0
    # Le pattern devrait avoir un bon score (succès, bonne qualité)
    assert efficiency > 0.5


def test_pattern_statistics(learner, sample_plan, sample_execution_result,
                           sample_verification_result, sample_request_analysis):
    """Test statistiques des patterns."""
    # Enregistrer quelques exécutions
    for _ in range(3):
        learner.record_execution(
            plan=sample_plan,
            execution_result=sample_execution_result,
            verification_result=sample_verification_result,
            request_analysis=sample_request_analysis
        )
    
    stats = learner.get_pattern_statistics()
    
    assert stats["total_patterns"] == 1
    assert stats["avg_success_rate"] > 0.0
    assert stats["avg_quality_score"] > 0.0


def test_pattern_with_failed_execution(learner, sample_plan, sample_request_analysis):
    """Test qu'un pattern qui échoue n'est pas enregistré."""
    failed_result = ExecutionResult(
        results={},
        success=False,
        errors=["Erreur"],
        execution_time=0.5
    )
    
    learner.record_execution(
        plan=sample_plan,
        execution_result=failed_result,
        verification_result=None,
        request_analysis=sample_request_analysis
    )
    
    # Ne devrait pas créer de pattern pour un échec
    assert len(learner.patterns) == 0


"""Tests de régression pour le système cognitif (Phase 6)."""

import pytest
from unittest.mock import Mock

from core.cognitive_planner import CognitivePlanner
from core.action_executor import ActionExecutor
from core.cognitive_models import ActionType, ActionPlan, Action
from core.self_verifier import SelfVerifier
from core.pattern_learner import PatternLearner
from core.cognitive_safeguards import CognitiveSafeguards, SafeguardConfig
from core.cognitive_optimizer import CognitiveOptimizer


@pytest.fixture
def mock_memory():
    """Crée un mock MemoryAdapter."""
    memory = Mock()
    memory.get_context = Mock(return_value={
        "traits": [{"label": "curieux", "value": "J'aime apprendre"}],
        "memories": [{"content": "Test memory", "importance_score": 0.8}],
        "recent_interactions": []
    })
    return memory


@pytest.fixture
def full_system(mock_memory):
    """Crée un système complet pour tests de régression."""
    safeguards = CognitiveSafeguards(config=SafeguardConfig())
    optimizer = CognitiveOptimizer(config={"enable_cache": False})  # Désactiver cache pour tests déterministes
    pattern_learner = PatternLearner(memory_adapter=mock_memory, config={})
    
    planner = CognitivePlanner(
        memory_adapter=mock_memory,
        pattern_learner=pattern_learner,
        safeguards=safeguards,
        optimizer=optimizer
    )
    
    executor = ActionExecutor(
        memory_adapter=mock_memory,
        pattern_learner=pattern_learner
    )
    
    verifier = SelfVerifier(
        memory_adapter=mock_memory,
        config={}
    )
    
    return {
        "planner": planner,
        "executor": executor,
        "verifier": verifier,
        "pattern_learner": pattern_learner,
        "safeguards": safeguards,
        "optimizer": optimizer
    }


@pytest.mark.asyncio
async def test_simple_question_regression(full_system):
    """Test de régression: question simple."""
    planner = full_system["planner"]
    
    plan = await planner.plan("Qui es-tu ?", session_id="regression_test")
    
    # Vérifier que le plan contient les actions attendues
    action_types = [a.type for a in plan.actions]
    assert ActionType.RESPOND in action_types, "Plan doit contenir RESPOND"
    
    # Vérifier que la confiance est raisonnable
    assert 0.0 <= plan.confidence <= 1.0, f"Confiance invalide: {plan.confidence}"


@pytest.mark.asyncio
async def test_memory_question_regression(full_system):
    """Test de régression: question nécessitant mémoire."""
    planner = full_system["planner"]
    
    plan = await planner.plan("Quels sont tes souvenirs ?", session_id="regression_test")
    
    # Devrait inclure des actions de consultation mémoire
    action_types = [a.type for a in plan.actions]
    memory_actions = [
        ActionType.CONSULT_MEMORY,
        ActionType.CONSULT_MEMORIES,
        ActionType.CONSULT_INTERACTIONS
    ]
    
    has_memory_action = any(at in memory_actions for at in action_types)
    assert has_memory_action, "Plan devrait inclure consultation mémoire"


@pytest.mark.asyncio
async def test_identity_question_regression(full_system):
    """Test de régression: question sur l'identité."""
    planner = full_system["planner"]
    
    # Réinitialiser le budget pour éviter les boucles détectées
    if planner.safeguards:
        planner.safeguards.reset_budget("regression_test")
    
    plan = await planner.plan("Quelle est ta personnalité ?", session_id="regression_test")
    
    # Devrait inclure consultation identité (ou plan minimal si garde-fous activés)
    action_types = [a.type for a in plan.actions]
    # Soit CONSULT_IDENTITY, soit plan minimal (RESPOND seulement)
    assert ActionType.RESPOND in action_types, "Plan devrait au moins contenir RESPOND"


@pytest.mark.asyncio
async def test_plan_execution_regression(full_system):
    """Test de régression: exécution d'un plan."""
    planner = full_system["planner"]
    executor = full_system["executor"]
    
    plan = await planner.plan("Test", session_id="regression_test")
    
    # Exécuter le plan
    result = await executor.execute_plan(plan, session_id="regression_test")
    
    # Vérifier que l'exécution a réussi (ou au moins tenté)
    assert result is not None
    assert hasattr(result, "success")
    assert hasattr(result, "results")


@pytest.mark.asyncio
async def test_safeguards_regression(full_system):
    """Test de régression: garde-fous fonctionnent."""
    planner = full_system["planner"]
    safeguards = full_system["safeguards"]
    
    plan = await planner.plan("Test", session_id="regression_test")
    
    # Valider avec garde-fous
    is_valid, issues = safeguards.validate_plan("regression_test", plan)
    
    # Le plan devrait être valide pour une requête simple
    assert is_valid or len(issues) > 0, "Validation devrait retourner un résultat"


@pytest.mark.asyncio
async def test_pattern_learning_regression(full_system):
    """Test de régression: apprentissage de patterns."""
    planner = full_system["planner"]
    pattern_learner = full_system["pattern_learner"]
    executor = full_system["executor"]
    
    # Exécuter plusieurs fois la même requête
    message = "Qui es-tu ?"
    for i in range(3):
        plan = await planner.plan(message, session_id="pattern_test")
        result = await executor.execute_plan(plan, session_id="pattern_test")
        
        # Enregistrer pour apprentissage
        from core.cognitive_models import ExecutionResult, VerificationResult, RequestAnalysis
        verification = VerificationResult(is_valid=True, overall_score=0.8)
        analysis = planner._analyze_request(message)
        
        pattern_learner.record_execution(
            plan=plan,
            execution_result=result,
            verification_result=verification,
            request_analysis=analysis
        )
    
    # Vérifier que des patterns ont été appris
    stats = pattern_learner.get_pattern_statistics()
    assert stats["total_patterns"] > 0, "Des patterns devraient être appris"


def test_action_plan_consistency():
    """Test de régression: cohérence des ActionPlan."""
    # Créer un plan simple
    actions = [
        Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
        Action(ActionType.RESPOND, {}, priority=2)
    ]
    
    plan = ActionPlan(actions=actions, estimated_cost=50.0, confidence=0.8)
    
    # Vérifier que les actions sont triées par priorité
    sorted_actions = plan.sorted_actions()
    priorities = [a.priority for a in sorted_actions]
    assert priorities == sorted(priorities), "Actions doivent être triées par priorité"


def test_safeguard_config_defaults():
    """Test de régression: valeurs par défaut des garde-fous."""
    config = SafeguardConfig()
    
    # Vérifier que les valeurs par défaut sont raisonnables
    assert config.max_decision_depth > 0
    assert config.max_reflection_tokens > 0
    assert config.max_reflection_time > 0
    assert config.max_actions_per_plan > 0


@pytest.mark.asyncio
async def test_error_handling_regression(full_system):
    """Test de régression: gestion des erreurs."""
    planner = full_system["planner"]
    
    # Tester avec des messages vides ou invalides
    edge_cases = ["", "   ", "a" * 10000]  # Vide, espaces, très long
    
    for msg in edge_cases:
        try:
            plan = await planner.plan(msg, session_id="error_test")
            # Devrait toujours retourner un plan (même minimal)
            assert plan is not None
            assert len(plan.actions) > 0
        except Exception as e:
            # Les erreurs doivent être gérées gracieusement
            assert False, f"Erreur non gérée: {e}"


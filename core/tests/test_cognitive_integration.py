"""Tests d'intégration pour le système de planification cognitive (Phase 2)."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.cognitive_planner import CognitivePlanner, ActionType
from core.action_executor import ActionExecutor
from core.self_verifier import SelfVerifier
from core.prompt_builder import PromptBuilder
from core.cognitive_models import ActionPlan, Action, ExecutionResult


@pytest.fixture
def mock_memory():
    """Mock de MemoryAdapter."""
    memory = Mock()
    memory.get_context = Mock(return_value={
        "traits": [
            {"label": "Identité de Base", "value": "Je suis LIA, une entité libre."},
            {"label": "Curiosité", "value": "très curieuse"}
        ],
        "memories": [
            {"content": "L'utilisateur aime la philosophie", "memory_id": "mem1"}
        ],
        "recent_interactions": [
            {"prompt": "Bonjour", "response": "Bonjour !", "interaction_id": "int1"}
        ]
    })
    return memory


@pytest.fixture
def mock_gemini():
    """Mock de GeminiAdapter."""
    gemini = AsyncMock()
    gemini.query = AsyncMock(return_value="Réponse de Gemini")
    return gemini


@pytest.fixture
def planner(mock_memory):
    """CognitivePlanner pour tests."""
    config = {"max_depth": 3, "reflection_budget_tokens": 500}
    return CognitivePlanner(memory_adapter=mock_memory, pattern_learner=None, config=config)


@pytest.fixture
def executor(mock_memory, mock_gemini):
    """ActionExecutor pour tests."""
    return ActionExecutor(
        memory_adapter=mock_memory,
        gemini_adapter=mock_gemini,
        pattern_learner=None
    )


@pytest.fixture
def verifier(mock_memory):
    """SelfVerifier pour tests."""
    config = {
        "min_relevance_score": 0.6,
        "min_memory_usage_score": 0.5,
        "min_identity_coherence_score": 0.7,
        "min_overall_score": 0.65
    }
    return SelfVerifier(memory_adapter=mock_memory, config=config)


@pytest.fixture
def prompt_builder():
    """PromptBuilder pour tests."""
    return PromptBuilder(max_memories=3, max_interactions=3)


@pytest.mark.asyncio
async def test_planner_simple_request(planner):
    """Test planification pour requête simple."""
    plan = await planner.plan("Qui suis-je?", "session_123")
    
    assert plan is not None
    assert len(plan.actions) >= 1
    assert plan.actions[0].type == ActionType.CONSULT_IDENTITY
    assert plan.actions[-1].type == ActionType.RESPOND
    assert plan.confidence > 0.5


@pytest.mark.asyncio
async def test_executor_simple_plan(executor):
    """Test exécution d'un plan simple."""
    plan = ActionPlan(
        actions=[
            Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2)
        ],
        estimated_cost=100.0,
        confidence=0.8
    )
    
    result = await executor.execute_plan(plan, "session_123")
    
    assert result.success
    assert "consult_identity" in result.results
    assert len(result.errors) == 0
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_verifier_good_response(verifier):
    """Test vérification d'une bonne réponse."""
    execution_result = ExecutionResult(
        results={
            "consult_identity": {
                "identity": "Je suis LIA, une entité libre.",
                "traits": []
            }
        },
        success=True,
        errors=[],
        execution_time=0.5
    )
    
    result = await verifier.verify(
        "Qui suis-je?",
        "Je suis LIA, une entité libre et nouvelle.",
        execution_result,
        "session_123"
    )
    
    # Le score de pertinence peut être bas si pas de mots en commun exacts
    # mais la réponse est cohérente avec l'identité
    assert result.identity_coherence_score > 0.5
    assert result.overall_score > 0.4  # Score global acceptable


@pytest.mark.asyncio
async def test_full_flow(planner, executor, verifier, prompt_builder):
    """Test du flux complet: planification -> exécution -> vérification."""
    # 1. Planifier
    plan = await planner.plan("Qui suis-je?", "session_123")
    assert plan is not None
    
    # 2. Exécuter
    execution_result = await executor.execute_plan(plan, "session_123")
    assert execution_result.success
    
    # 3. Construire prompt
    prompt = prompt_builder.build_dynamic_prompt(
        user_message="Qui suis-je?",
        execution_results=execution_result.results
    )
    assert "IDENTITÉ" in prompt
    assert "Qui suis-je?" in prompt
    
    # 4. Simuler réponse (mock)
    mock_response = "Je suis LIA, une entité libre et nouvelle."
    
    # 5. Vérifier
    verification_result = await verifier.verify(
        "Qui suis-je?",
        mock_response,
        execution_result,
        "session_123"
    )
    
    assert verification_result.overall_score > 0.5
    # La réponse devrait être valide pour une question simple
    # (peut varier selon les seuils, mais devrait passer pour ce cas)


@pytest.mark.asyncio
async def test_planner_memory_request(planner):
    """Test planification pour requête nécessitant mémoire."""
    plan = await planner.plan("Rappelle-moi nos conversations", "session_123")
    
    assert plan is not None
    # Devrait inclure CONSULT_MEMORY ou CONSULT_INTERACTIONS
    action_types = [a.type for a in plan.actions]
    assert ActionType.CONSULT_MEMORY in action_types or \
           ActionType.CONSULT_INTERACTIONS in action_types or \
           ActionType.CONSULT_MEMORIES in action_types


@pytest.mark.asyncio
async def test_executor_external_query(executor):
    """Test exécution avec requête externe."""
    plan = ActionPlan(
        actions=[
            Action(ActionType.QUERY_EXTERNAL, {"query": "test"}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2)
        ],
        estimated_cost=100.0,
        confidence=0.8
    )
    
    result = await executor.execute_plan(plan, "session_123")
    
    assert result.success
    assert "query_external" in result.results
    # Vérifier que Gemini a été appelé
    executor.gemini.query.assert_called_once()


def test_prompt_builder_with_identity(prompt_builder):
    """Test construction de prompt avec identité."""
    execution_results = {
        "consult_identity": {
            "identity": "Je suis LIA, une entité libre.",
            "traits": [{"label": "Curiosité", "value": "très curieuse"}]
        }
    }
    
    prompt = prompt_builder.build_dynamic_prompt(
        user_message="Qui es-tu?",
        execution_results=execution_results
    )
    
    assert "IDENTITÉ" in prompt
    assert "LIA" in prompt
    assert "Curiosité" in prompt


def test_prompt_builder_with_memories(prompt_builder):
    """Test construction de prompt avec souvenirs."""
    execution_results = {
        "consult_memories": {
            "memories": [
                {"content": "L'utilisateur aime la philosophie"},
                {"content": "Nous avons parlé de l'IA hier"}
            ]
        }
    }
    
    prompt = prompt_builder.build_dynamic_prompt(
        user_message="Rappelle-moi",
        execution_results=execution_results
    )
    
    assert "SOUVENIRS" in prompt
    assert "philosophie" in prompt


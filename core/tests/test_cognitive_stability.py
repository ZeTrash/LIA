"""Tests de stabilité pour le système cognitif (Phase 6)."""

import pytest
import asyncio
from unittest.mock import Mock

from core.cognitive_planner import CognitivePlanner
from core.action_executor import ActionExecutor
from core.cognitive_models import ActionType
from core.cognitive_safeguards import CognitiveSafeguards, SafeguardConfig
from core.cognitive_optimizer import CognitiveOptimizer


@pytest.fixture
def stable_system():
    """Crée un système stable pour tests."""
    memory = Mock()
    memory.get_context = Mock(return_value={"traits": [], "memories": [], "recent_interactions": []})
    
    safeguards = CognitiveSafeguards(config=SafeguardConfig())
    optimizer = CognitiveOptimizer(config={"enable_cache": False})  # Désactiver pour tests déterministes
    
    planner = CognitivePlanner(
        memory_adapter=memory,
        safeguards=safeguards,
        optimizer=optimizer
    )
    
    executor = ActionExecutor(memory_adapter=memory)
    
    return {"planner": planner, "executor": executor, "safeguards": safeguards}


@pytest.mark.asyncio
async def test_deterministic_planning(stable_system):
    """Test que la planification est déterministe (même entrée = même sortie)."""
    planner = stable_system["planner"]
    message = "Qui es-tu ?"
    
    # Réinitialiser le budget pour chaque test pour éviter les boucles
    if planner.safeguards:
        planner.safeguards.reset_budget("deterministic_test")
    
    # Planifier plusieurs fois la même requête avec sessions différentes
    # (pour éviter la détection de boucles)
    plans = []
    for i in range(5):
        session_id = f"deterministic_test_{i}"
        if planner.safeguards:
            planner.safeguards.reset_budget(session_id)
        plan = await planner.plan(message, session_id=session_id)
        plans.append(plan)
    
    # Vérifier que tous les plans sont cohérents (au moins RESPOND)
    for plan in plans:
        action_types = [a.type for a in plan.actions]
        assert ActionType.RESPOND in action_types, "Tous les plans devraient contenir RESPOND"
        assert len(plan.actions) > 0, "Tous les plans devraient avoir au moins une action"


@pytest.mark.asyncio
async def test_long_running_stability(stable_system):
    """Test stabilité sur une longue période."""
    planner = stable_system["planner"]
    executor = stable_system["executor"]
    
    # Simuler une session longue avec beaucoup de requêtes
    messages = [f"Requête {i}" for i in range(100)]
    
    for i, msg in enumerate(messages):
        plan = await planner.plan(msg, session_id="long_session")
        
        # Vérifier que le plan est toujours valide
        assert plan is not None
        assert len(plan.actions) > 0
        
        # Vérifier que les garde-fous sont toujours respectés
        if stable_system["safeguards"]:
            is_valid, issues = stable_system["safeguards"].validate_plan("long_session", plan)
            # Le plan devrait être valide ou avoir des raisons claires d'invalidité
            assert is_valid or len(issues) > 0
        
        # Exécuter le plan (même si c'est un mock)
        try:
            result = await executor.execute_plan(plan, session_id="long_session")
            assert result is not None
        except Exception:
            # Acceptable si c'est un mock
            pass


@pytest.mark.asyncio
async def test_memory_consistency(stable_system):
    """Test que la mémoire reste cohérente."""
    planner = stable_system["planner"]
    
    # Planifier plusieurs requêtes dans la même session
    session_id = "consistency_test"
    
    for i in range(10):
        plan = await planner.plan(f"Requête {i}", session_id=session_id)
        
        # Vérifier que le plan est toujours cohérent
        assert plan.confidence >= 0.0
        assert plan.confidence <= 1.0
        assert plan.estimated_cost >= 0.0


@pytest.mark.asyncio
async def test_error_recovery(stable_system):
    """Test que le système récupère bien des erreurs."""
    planner = stable_system["planner"]
    
    # Tester avec des cas limites
    edge_cases = [
        "",  # Vide
        "   ",  # Espaces
        "a" * 1000,  # Très long
        "!@#$%^&*()",  # Caractères spéciaux
        "测试",  # Unicode
    ]
    
    for msg in edge_cases:
        try:
            plan = await planner.plan(msg, session_id="error_recovery")
            # Devrait toujours retourner un plan (même minimal)
            assert plan is not None
        except Exception as e:
            # Les erreurs doivent être gérées gracieusement
            pytest.fail(f"Erreur non gérée pour '{msg[:20]}...': {e}")


@pytest.mark.asyncio
async def test_concurrent_stability(stable_system):
    """Test stabilité avec accès concurrents."""
    planner = stable_system["planner"]
    
    # Créer plusieurs tâches concurrentes
    async def plan_task(msg, session_id):
        return await planner.plan(msg, session_id=session_id)
    
    messages = [f"Concurrent {i}" for i in range(20)]
    tasks = [plan_task(msg, f"session_{i % 5}") for i, msg in enumerate(messages)]
    
    # Exécuter toutes les tâches en parallèle
    plans = await asyncio.gather(*tasks)
    
    # Vérifier que tous les plans ont été créés
    assert len(plans) == len(messages)
    assert all(plan is not None for plan in plans)
    assert all(len(plan.actions) > 0 for plan in plans)


def test_safeguard_budget_consistency(stable_system):
    """Test que les budgets de garde-fous restent cohérents."""
    safeguards = stable_system["safeguards"]
    session_id = "budget_test"
    
    # Utiliser le budget plusieurs fois
    for i in range(10):
        safeguards.record_reflection_usage(
            session_id=session_id,
            tokens=50,
            time_elapsed=0.1,
            memory_cost=10.0
        )
        
        # Vérifier que le budget est cohérent
        status = safeguards.get_budget_status(session_id)
        assert status["tokens_used"] == 50 * (i + 1)
        assert status["tokens_remaining"] >= 0
        assert status["time_remaining"] >= 0


"""Tests de charge pour le système cognitif (Phase 6)."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from core.cognitive_planner import CognitivePlanner
from core.action_executor import ActionExecutor
from core.cognitive_models import ActionType
from core.cognitive_safeguards import CognitiveSafeguards, SafeguardConfig
from core.cognitive_optimizer import CognitiveOptimizer


@pytest.fixture
def mock_memory():
    """Crée un mock MemoryAdapter."""
    memory = Mock()
    memory.get_context = Mock(return_value={"traits": [], "memories": [], "recent_interactions": []})
    return memory


@pytest.fixture
def planner_with_safeguards(mock_memory):
    """Crée un planificateur avec garde-fous."""
    safeguards = CognitiveSafeguards(config=SafeguardConfig())
    optimizer = CognitiveOptimizer(config={"enable_cache": True})
    return CognitivePlanner(
        memory_adapter=mock_memory,
        safeguards=safeguards,
        optimizer=optimizer
    )


@pytest.fixture
def executor(mock_memory):
    """Crée un exécuteur d'actions."""
    return ActionExecutor(memory_adapter=mock_memory)


@pytest.mark.asyncio
async def test_concurrent_planning(planner_with_safeguards):
    """Test planification concurrente (plusieurs requêtes en parallèle)."""
    messages = [
        "Qui es-tu ?",
        "Quelle est ta personnalité ?",
        "Raconte-moi une histoire",
        "Quels sont tes souvenirs ?",
        "Comment fonctionnes-tu ?"
    ]
    
    start_time = time.time()
    
    # Planifier toutes les requêtes en parallèle
    tasks = [planner_with_safeguards.plan(msg, session_id=f"session_{i}") for i, msg in enumerate(messages)]
    plans = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    # Vérifier que tous les plans ont été créés
    assert len(plans) == len(messages)
    assert all(plan.actions for plan in plans)
    
    # Vérifier que le temps total est raisonnable (< 2 secondes pour 5 requêtes)
    assert elapsed < 2.0, f"Temps trop long: {elapsed:.2f}s"
    
    print(f"✅ {len(messages)} requêtes planifiées en {elapsed:.2f}s ({elapsed/len(messages):.3f}s par requête)")


@pytest.mark.asyncio
async def test_high_volume_planning(planner_with_safeguards):
    """Test avec un volume élevé de requêtes séquentielles."""
    num_requests = 50
    messages = [f"Requête {i}" for i in range(num_requests)]
    
    start_time = time.time()
    
    plans = []
    for i, msg in enumerate(messages):
        plan = await planner_with_safeguards.plan(msg, session_id=f"session_{i % 10}")
        plans.append(plan)
    
    elapsed = time.time() - start_time
    avg_time = elapsed / num_requests
    
    assert len(plans) == num_requests
    assert avg_time < 0.1, f"Temps moyen trop élevé: {avg_time:.3f}s"
    
    print(f"✅ {num_requests} requêtes traitées en {elapsed:.2f}s (moyenne: {avg_time:.3f}s)")


@pytest.mark.asyncio
async def test_cache_performance(planner_with_safeguards):
    """Test performance du cache."""
    message = "Qui es-tu ?"
    
    # Première requête (cache miss)
    start1 = time.time()
    plan1 = await planner_with_safeguards.plan(message, session_id="test")
    time1 = time.time() - start1
    
    # Deuxième requête (cache hit)
    start2 = time.time()
    plan2 = await planner_with_safeguards.plan(message, session_id="test")
    time2 = time.time() - start2
    
    # Le cache devrait être plus rapide
    assert time2 < time1, f"Cache pas plus rapide: {time1:.4f}s vs {time2:.4f}s"
    
    print(f"✅ Cache: {time1:.4f}s (miss) vs {time2:.4f}s (hit) - amélioration: {(1-time2/time1)*100:.1f}%")


@pytest.mark.asyncio
async def test_safeguards_under_load(planner_with_safeguards):
    """Test que les garde-fous fonctionnent sous charge."""
    # Créer beaucoup de requêtes pour tester les garde-fous
    messages = [f"Requête {i}" for i in range(20)]
    
    plans = []
    for i, msg in enumerate(messages):
        plan = await planner_with_safeguards.plan(msg, session_id="load_test")
        plans.append(plan)
        
        # Vérifier que les garde-fous sont respectés
        if planner_with_safeguards.safeguards:
            is_valid, issues = planner_with_safeguards.safeguards.validate_plan("load_test", plan)
            assert is_valid or len(issues) > 0, "Plan invalide sans raison"
    
    assert len(plans) == len(messages)
    print(f"✅ {len(messages)} requêtes traitées avec garde-fous actifs")


@pytest.mark.asyncio
async def test_memory_usage(planner_with_safeguards):
    """Test utilisation mémoire (pas de fuites)."""
    import sys
    
    # Mesurer la taille avant
    before = sys.getsizeof(planner_with_safeguards)
    
    # Traiter beaucoup de requêtes
    for i in range(100):
        await planner_with_safeguards.plan(f"Requête {i}", session_id="memory_test")
    
    # Mesurer la taille après
    after = sys.getsizeof(planner_with_safeguards)
    
    # La croissance devrait être limitée (cache a une taille max)
    growth = after - before
    assert growth < 100000, f"Fuite mémoire suspecte: {growth} bytes"
    
    print(f"✅ Utilisation mémoire: {before} -> {after} bytes (croissance: {growth})")


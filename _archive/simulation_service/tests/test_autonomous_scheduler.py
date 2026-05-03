"""Tests pour le scheduler autonome (Étape 2.6)."""

import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ajouter le répertoire src au PYTHONPATH
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from simulation_service.autonomous_scheduler import (
    LIAAutonomousScheduler,
    AutonomousConfig,
    SchedulerStatus
)
from simulation_service.orchestrator import SimulationOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Orchestrateur mock."""
    return MagicMock(spec=SimulationOrchestrator)


@pytest.fixture
def scheduler_config():
    """Configuration de test avec intervalles courts."""
    return AutonomousConfig(
        enabled=True,
        goals_check_seconds=1,  # 1 seconde pour tests
        auto_research_hours=0,  # 0 heures = immédiat
        auto_reflection_hours=0,
        auto_evaluation_hours=0,
        max_retries=2,
        retry_delay_seconds=1,
    )


@pytest.fixture
def scheduler(mock_orchestrator, scheduler_config):
    """Scheduler de test."""
    with patch('simulation_service.autonomous_scheduler.httpx.AsyncClient') as mock_client:
        mock_client_instance = AsyncMock()
        mock_client.return_value = mock_client_instance
        
        scheduler = LIAAutonomousScheduler(
            memory_service_url="http://localhost:8000",
            orchestrator=mock_orchestrator,
            config=scheduler_config,
        )
        scheduler.memory_client = mock_client_instance
        return scheduler


def test_scheduler_initialization(scheduler):
    """Test d'initialisation du scheduler."""
    assert scheduler.config.enabled is True
    assert scheduler.running is False
    assert scheduler.status.running is False


def test_scheduler_status(scheduler):
    """Test du statut du scheduler."""
    status = scheduler.get_status()
    assert isinstance(status, SchedulerStatus)
    assert status.running is False
    assert status.actions_triggered_total == 0
    assert status.errors_count == 0


@pytest.mark.asyncio
async def test_check_personal_goals_no_goals(scheduler):
    """Test de vérification des objectifs (aucun objectif)."""
    # Mock réponse vide
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value=[])
    mock_response.raise_for_status = MagicMock()
    scheduler.memory_client.get = AsyncMock(return_value=mock_response)
    
    await scheduler.check_personal_goals()
    
    # Vérifier que l'appel a été fait
    scheduler.memory_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_check_personal_goals_with_goals(scheduler):
    """Test de vérification des objectifs (avec objectifs)."""
    from datetime import datetime, UTC, timedelta
    
    now = datetime.now(UTC)
    past_time = (now - timedelta(hours=1)).isoformat()
    
    # Mock réponse avec objectif à déclencher
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value=[
        {
            "goal_id": "goal-test-1",
            "goal_type": "research",
            "description": "Test research",
            "frequency": "once",
            "next_trigger_at": past_time,
            "status": "active",
        }
    ])
    mock_response.raise_for_status = MagicMock()
    scheduler.memory_client.get = AsyncMock(return_value=mock_response)
    
    mock_put_response = AsyncMock()
    mock_put_response.raise_for_status = MagicMock()
    scheduler.memory_client.put = AsyncMock(return_value=mock_put_response)
    
    # Mock trigger_auto_research
    scheduler.trigger_auto_research = AsyncMock()
    
    await scheduler.check_personal_goals()
    
    # Vérifier que trigger_auto_research a été appelé
    scheduler.trigger_auto_research.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_auto_research(scheduler):
    """Test de déclenchement auto-recherche."""
    # Mock portail autonome
    scheduler.autonomous_portal.choose_research_topic = AsyncMock(return_value="test topic")
    scheduler.autonomous_portal.research_topic = AsyncMock()
    scheduler.autonomous_portal._get_memory_context = AsyncMock(return_value={})
    
    await scheduler.trigger_auto_research()
    
    # Vérifier que research_topic a été appelé
    scheduler.autonomous_portal.research_topic.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_auto_evaluation(scheduler):
    """Test de déclenchement auto-évaluation."""
    # Mock portail multi-agent
    scheduler.multi_agent_portal.trigger_auto_evaluation = AsyncMock(return_value="session-123")
    
    await scheduler.trigger_auto_evaluation()
    
    # Vérifier que trigger_auto_evaluation a été appelé
    scheduler.multi_agent_portal.trigger_auto_evaluation.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_auto_reflection(scheduler):
    """Test de déclenchement auto-réflexion."""
    # Mock portail autonome
    scheduler.autonomous_portal.reflect_on_interactions = AsyncMock(return_value={"insights": "test"})
    
    await scheduler.trigger_auto_reflection()
    
    # Vérifier que reflect_on_interactions a été appelé
    scheduler.autonomous_portal.reflect_on_interactions.assert_called_once_with(window_hours=24)


@pytest.mark.asyncio
async def test_safe_execute_success(scheduler):
    """Test de _safe_execute avec succès."""
    mock_action = AsyncMock()
    
    await scheduler._safe_execute(mock_action, "test_action")
    
    assert scheduler.status.actions_triggered_total == 1
    mock_action.assert_called_once()


@pytest.mark.asyncio
async def test_safe_execute_error(scheduler):
    """Test de _safe_execute avec erreur."""
    mock_action = AsyncMock(side_effect=Exception("Test error"))
    
    await scheduler._safe_execute(mock_action, "test_action")
    
    assert scheduler.status.errors_count == 1
    # actions_triggered_total ne devrait pas être incrémenté en cas d'erreur
    assert scheduler.status.actions_triggered_total == 0


@pytest.mark.asyncio
async def test_stop_scheduler(scheduler):
    """Test d'arrêt du scheduler."""
    scheduler.running = True
    scheduler.memory_client.aclose.reset_mock()  # Reset pour compter seulement les appels de stop()
    
    await scheduler.stop()
    
    assert scheduler.running is False
    assert scheduler.status.running is False
    # Vérifier qu'aclose a été appelé au moins une fois (peut être appelé plusieurs fois si le scheduler était déjà en cours d'arrêt)
    assert scheduler.memory_client.aclose.call_count >= 1

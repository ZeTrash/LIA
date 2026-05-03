"""Tests pour le calcul des métriques."""

import sys
from pathlib import Path

import pytest

# Ajouter le répertoire src au PYTHONPATH pour permettre l'import de simulation_service
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from simulation_service.metrics import (
    calculate_variability,
    calculate_autonomy,
    calculate_curiosity,
    calculate_coherence,
    calculate_all_metrics,
    is_question,
    extract_topics
)
from simulation_service.protocol import generate_message_id, generate_session_id
from simulation_service.schemas import MultiAgentMessage


@pytest.fixture
def sample_messages():
    """Messages de test."""
    session_id = generate_session_id()
    return [
        MultiAgentMessage(
            message_id=generate_message_id(),
            session_id=session_id,
            agent_id="agent1",
            agent_partner_id="agent2",
            content="Bonjour, comment vas-tu ?",
            metadata={"scores": {"coherence": 0.9}}
        ),
        MultiAgentMessage(
            message_id=generate_message_id(),
            session_id=session_id,
            agent_id="agent2",
            agent_partner_id="agent1",
            content="Je vais bien, merci !",
            metadata={"scores": {"coherence": 0.85}}
        ),
        MultiAgentMessage(
            message_id=generate_message_id(),
            session_id=session_id,
            agent_id="agent1",
            agent_partner_id="agent2",
            content="Qu'est-ce que tu penses de la philosophie ?",
            metadata={"scores": {"coherence": 0.92}}
        )
    ]


def test_is_question():
    """Test de détection de question."""
    assert is_question("Comment vas-tu ?") is True
    assert is_question("Je vais bien.") is False
    assert is_question("Qu'est-ce que tu penses ?") is True


def test_extract_topics():
    """Test d'extraction de sujets."""
    topics = extract_topics("Je parle de philosophie et de science.")
    assert len(topics) > 0


def test_calculate_variability(sample_messages):
    """Test de calcul de variabilité."""
    variability = calculate_variability(sample_messages)
    assert 0.0 <= variability <= 1.0


def test_calculate_autonomy(sample_messages):
    """Test de calcul d'autonomie."""
    autonomy = calculate_autonomy(sample_messages, "agent1")
    assert 0.0 <= autonomy <= 1.0


def test_calculate_curiosity(sample_messages):
    """Test de calcul de curiosité."""
    curiosity = calculate_curiosity(sample_messages, "agent1")
    assert 0.0 <= curiosity <= 1.0


def test_calculate_coherence(sample_messages):
    """Test de calcul de cohérence."""
    coherence = calculate_coherence(sample_messages, "agent1")
    assert 0.0 <= coherence <= 1.0


def test_calculate_all_metrics(sample_messages):
    """Test de calcul de toutes les métriques."""
    metrics = calculate_all_metrics(sample_messages, agent_id="agent1")
    assert metrics.variability >= 0.0
    assert metrics.autonomy >= 0.0
    assert metrics.curiosity >= 0.0
    assert metrics.coherence >= 0.0

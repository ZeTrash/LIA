"""Tests pour le protocole de communication."""

import sys
from datetime import datetime, UTC
from pathlib import Path

import pytest

# Ajouter le répertoire src au PYTHONPATH pour permettre l'import de simulation_service
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from simulation_service.protocol import (
    validate_message,
    validate_handshake,
    generate_message_id,
    generate_session_id,
    detect_loop,
    calculate_content_hash
)
from simulation_service.schemas import MultiAgentMessage, AgentHandshake


def test_generate_message_id():
    """Test de génération d'ID de message."""
    msg_id = generate_message_id()
    assert msg_id.startswith("msg-")
    assert len(msg_id) == 16  # msg-YYYYMMDD-XXX


def test_generate_session_id():
    """Test de génération d'ID de session."""
    session_id = generate_session_id()
    assert session_id.startswith("sim-")
    assert len(session_id) == 16  # sim-YYYYMMDD-XXX


def test_validate_message():
    """Test de validation d'un message."""
    message_data = {
        "message_id": "msg-20241207-001",
        "session_id": "sim-20241207-001",
        "agent_id": "agent1",
        "agent_partner_id": "agent2",
        "timestamp": datetime.now(UTC).isoformat(),
        "message_type": "text",
        "content": "Bonjour"
    }
    
    is_valid, error = validate_message(message_data)
    assert is_valid
    assert error is None


def test_detect_loop():
    """Test de détection de boucle."""
    from simulation_service.schemas import MultiAgentMessage
    from simulation_service.protocol import generate_session_id
    
    session_id = generate_session_id()
    # Créer 3 messages identiques avec des IDs différents mais même contenu
    messages = [
        MultiAgentMessage(
            message_id=f"msg-20241207-{i:03d}",
            session_id=session_id,
            agent_id="agent1",
            agent_partner_id="agent2",
            content="Message identique"
        )
        for i in range(3)
    ]
    
    assert detect_loop(messages, threshold=3) is True
    
    # Messages différents
    messages[2].content = "Message différent"
    assert detect_loop(messages, threshold=3) is False


def test_calculate_content_hash():
    """Test de calcul de hash."""
    content = "Test message"
    hash1 = calculate_content_hash(content)
    hash2 = calculate_content_hash(content)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 = 64 caractères hex

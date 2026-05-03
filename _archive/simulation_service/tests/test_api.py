"""Tests de base pour l'API."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ajouter le répertoire src au PYTHONPATH pour permettre l'import de simulation_service
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from simulation_service.api import create_app


@pytest.fixture
def client():
    """Client de test pour l'API."""
    app = create_app()
    return TestClient(app)


def test_health(client: TestClient):
    """Test de l'endpoint de santé."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data


def test_start_simulation(client: TestClient):
    """Test de démarrage d'une simulation."""
    payload = {
        "agent_configs": [
            {"agent_id": "agent1", "agent_type": "simulated"},
            {"agent_id": "agent2", "agent_type": "simulated"}
        ],
        "max_turns": 5
    }
    
    response = client.post("/simulation/start", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["status"] in ["running", "starting"]
    assert len(data["agents"]) == 2

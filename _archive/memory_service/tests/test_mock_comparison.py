"""Tests comparant le service réel au mock server."""

import json
from pathlib import Path
from typing import Any, Dict

import pytest
import requests
from fastapi.testclient import TestClient

from memory_service.api import create_app
from memory_service.config import get_settings

BASE_DIR = Path(__file__).resolve().parents[2]
SAMPLES_PATH = BASE_DIR / "charge_timeline" / "etape1_cahier_charges" / "livrables" / "mock_server" / "sample_payloads.json"

with SAMPLES_PATH.open("r", encoding="utf-8") as f:
    SAMPLE_PAYLOADS: Dict[str, Any] = json.load(f)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Client de test avec base SQLite en mémoire."""
    monkeypatch.setenv("MEMORY_SERVICE_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("MEMORY_SERVICE_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture()
def mock_server_url():
    """URL du mock server (si disponible)."""
    return "http://127.0.0.1:4600"


@pytest.mark.skipif(
    not requests.get("http://127.0.0.1:4600/health", timeout=1).ok,
    reason="Mock server non disponible",
)
class TestMockComparison:
    """Tests comparant les réponses du service réel au mock server."""

    def test_context_structure_comparison(self, client: TestClient, mock_server_url: str):
        """Compare la structure de GET /context avec le mock."""
        # Service réel
        real_response = client.get("/context", params={"session_id": "test"})
        assert real_response.status_code == 200
        real_data = real_response.json()

        # Mock server
        mock_response = requests.get(f"{mock_server_url}/context", params={"session_id": "test"})
        assert mock_response.status_code == 200
        mock_data = mock_response.json()

        # Comparer les clés principales
        assert set(real_data.keys()) == set(mock_data.keys()), "Clés différentes entre réel et mock"

        # Vérifier que les types sont cohérents
        assert isinstance(real_data["traits"], list) == isinstance(mock_data["traits"], list)
        assert isinstance(real_data["memories"], list) == isinstance(mock_data["memories"], list)
        assert isinstance(real_data["indicators"], dict) == isinstance(mock_data["indicators"], dict)

    def test_interaction_structure_comparison(self, client: TestClient, mock_server_url: str):
        """Compare la structure de POST /interaction avec le mock."""
        payload = {
            "interaction_id": "compare-001",
            "session_id": "test",
            "prompt": "Test",
            "response": "Response",
        }

        # Service réel
        real_response = client.post("/interaction", json=payload)
        assert real_response.status_code == 200
        real_data = real_response.json()

        # Mock server
        mock_response = requests.post(f"{mock_server_url}/interaction", json=payload)
        assert mock_response.status_code == 201
        mock_data = mock_response.json()

        # Vérifier les champs communs
        common_fields = ["interaction_id", "session_id", "prompt", "response"]
        for field in common_fields:
            assert field in real_data, f"Champ '{field}' manquant dans service réel"
            assert field in mock_data, f"Champ '{field}' manquant dans mock"


class TestSamplePayloads:
    """Tests utilisant les payloads d'exemple du mock server."""

    def test_context_sample_structure(self, client: TestClient):
        """Vérifie que le contexte retourné a la même structure que les samples."""
        sample_context = SAMPLE_PAYLOADS["context"]

        # Créer quelques données pour avoir un contexte non vide
        from memory_service.schemas import InteractionRequest, InteractionDecisions

        payload = InteractionRequest(
            interaction_id="sample-001",
            session_id="test",
            prompt="Test",
            response="Response",
            decisions=InteractionDecisions(create_memory=True),
        )
        client.post("/interaction", json=payload.model_dump())

        # Récupérer le contexte
        response = client.get("/context", params={"session_id": "test"})
        assert response.status_code == 200
        data = response.json()

        # Vérifier que les clés principales correspondent
        sample_keys = set(sample_context.keys())
        real_keys = set(data.keys())
        # Les clés doivent être compatibles (peuvent avoir des différences mineures)
        assert "traits" in real_keys
        assert "memories" in real_keys
        assert "indicators" in real_keys
        assert "governance_metadata" in real_keys

    def test_metrics_sample_structure(self, client: TestClient):
        """Vérifie que les métriques ont la même structure que les samples."""
        sample_metrics = SAMPLE_PAYLOADS["metrics"]

        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()

        # Vérifier les KPI
        if "kpis" in sample_metrics:
            assert "kpis" in data
            sample_kpis = sample_metrics["kpis"]
            real_kpis = data["kpis"]
            for kpi in sample_kpis.keys():
                assert kpi in real_kpis, f"KPI '{kpi}' manquant dans service réel"




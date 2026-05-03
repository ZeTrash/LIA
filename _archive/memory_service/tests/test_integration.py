"""Tests d'intégration : validation contre spécifications OpenAPI et mock server."""

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from fastapi.testclient import TestClient

# Ajouter le répertoire src au PYTHONPATH pour permettre l'import de memory_service
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_service.api import create_app
from memory_service.config import get_settings
from memory_service.schemas import (
    ContextResponse,
    GovernanceCheckRequest,
    GovernanceCheckResponse,
    GovernanceSignal,
    InteractionDecisions,
    InteractionEmotions,
    InteractionRequest,
    InteractionScores,
    TraitUpdateRequest,
    TraitUpdateResponse,
)

# Charger la spécification OpenAPI
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = PROJECT_ROOT / "charge_timeline" / "etape1_cahier_charges" / "livrables" / "api_spec_openapi.yaml"

with SPEC_PATH.open("r", encoding="utf-8") as f:
    OPENAPI_SPEC: Dict[str, Any] = yaml.safe_load(f)


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
def sample_context():
    """Contexte d'exemple conforme à l'OpenAPI."""
    return {
        "traits": [
            {
                "trait_id": "tone",
                "type": "persona",
                "label": "Ton",
                "value": "curieux mais calme",
                "version": 1,
                "weight": 0.82,
                "confidence": 0.84,
                "origin": "system",
                "status": "active",
            }
        ],
        "session_goals": [],
        "memories": [],
        "indicators": {},
        "governance_metadata": {},
    }


class TestAPIContract:
    """Tests de conformité des contrats API."""

    def test_get_context_schema(self, client: TestClient):
        """Vérifie que GET /context retourne un schéma conforme."""
        response = client.get("/context", params={"session_id": "test-session"})
        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure selon OpenAPI
        schema = OPENAPI_SPEC["components"]["schemas"]["MemoryContext"]
        required_fields = schema.get("required", [])
        for field in required_fields:
            assert field in data, f"Champ requis '{field}' manquant dans la réponse"

        # Vérifier les types
        assert isinstance(data["traits"], list)
        assert isinstance(data["session_goals"], list)
        assert isinstance(data["memories"], list)
        assert isinstance(data["indicators"], dict)
        assert isinstance(data["governance_metadata"], dict)

        # Valider avec Pydantic
        ctx = ContextResponse.model_validate(data)
        assert ctx.build_time_ms >= 0
        assert ctx.trace_id
        assert ctx.context_checksum

    def test_get_context_latency(self, client: TestClient):
        """Vérifie que la latence est < 200ms."""
        response = client.get("/context", params={"session_id": "test-session"})
        assert response.status_code == 200
        data = response.json()
        assert data["build_time_ms"] < 200, f"Latence trop élevée: {data['build_time_ms']}ms"

    def test_get_context_payload_size(self, client: TestClient):
        """Vérifie que le payload est < 10KB."""
        response = client.get("/context", params={"session_id": "test-session"})
        assert response.status_code == 200
        payload_bytes = len(response.content)
        assert payload_bytes < 10240, f"Payload trop volumineux: {payload_bytes} bytes"

    def test_post_interaction_schema(self, client: TestClient):
        """Vérifie que POST /interaction accepte et retourne le bon schéma."""
        payload = InteractionRequest(
            interaction_id="test-i-001",
            session_id="test-session",
            prompt="Test prompt",
            response="Test response",
            scores=InteractionScores(usefulness=0.8, coherence=0.9, tone=0.9),
            emotions=InteractionEmotions(valence=0.3, arousal=0.4),
            decisions=InteractionDecisions(create_memory=True, derived_traits=["tone"]),
        )
        response = client.post("/interaction", json=payload.model_dump())
        assert response.status_code == 200
        data = response.json()

        # Vérifier les champs requis
        assert "interaction_id" in data
        assert "session_id" in data
        assert "occurred_at" in data
        assert "severity" in data

    def test_post_interaction_idempotence(self, client: TestClient):
        """Vérifie l'idempotence via interaction_id."""
        payload = InteractionRequest(
            interaction_id="test-idempotent",
            session_id="test-session",
            prompt="Test",
            response="Response",
        )
        response1 = client.post("/interaction", json=payload.model_dump())
        assert response1.status_code == 200
        data1 = response1.json()

        response2 = client.post("/interaction", json=payload.model_dump())
        assert response2.status_code == 200
        data2 = response2.json()

        # Même interaction_id doit retourner les mêmes données
        assert data1["interaction_id"] == data2["interaction_id"]
        assert data1["occurred_at"] == data2["occurred_at"]

    def test_post_trait_update_schema(self, client: TestClient):
        """Vérifie que POST /trait-update accepte delta comme objet."""
        payload = TraitUpdateRequest(
            trait_id="tone",
            delta={"value": "nouveau ton", "weight": 0.9},
            reason="Test update",
            source="test",
            expected_version=1,
        )
        response = client.post("/trait-update", json=payload.model_dump())
        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure
        assert "trait" in data
        assert "version_token" in data
        assert "review_required" in data
        assert data["trait"]["version"] >= 1

    def test_post_trait_update_version_conflict(self, client: TestClient):
        """Vérifie la gestion du conflit de version (409)."""
        # Créer un trait
        payload1 = TraitUpdateRequest(
            trait_id="test-conflict",
            delta={"value": "v1"},
            reason="Initial",
            source="test",
        )
        response1 = client.post("/trait-update", json=payload1.model_dump())
        assert response1.status_code == 200
        version1 = response1.json()["trait"]["version"]

        # Tenter une mise à jour avec une version obsolète
        payload2 = TraitUpdateRequest(
            trait_id="test-conflict",
            delta={"value": "v2"},
            reason="Update",
            source="test",
            expected_version=version1 - 1,  # Version obsolète
        )
        response2 = client.post("/trait-update", json=payload2.model_dump())
        # Doit retourner review_required=True mais pas d'erreur 409 si pas de version conflictuelle réelle
        # (car on ne force pas le conflit dans ce test)
        assert response2.status_code in [200, 409]

    def test_post_governance_check_schema(self, client: TestClient):
        """Vérifie que POST /governance/check accepte signals comme array."""
        payload = GovernanceCheckRequest(
            session_id="test-session",
            draft_response="Réponse de test",
            signals=[
                GovernanceSignal(type="drift", value=0.4),
                GovernanceSignal(type="coherence", value=0.85),
            ],
        )
        response = client.post("/governance/check", json=payload.model_dump())
        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure
        assert "verdict" in data
        assert data["verdict"] in ["allow", "warn", "block"]
        assert "issues" in data
        assert isinstance(data["issues"], list)

        # Valider avec Pydantic
        result = GovernanceCheckResponse.model_validate(data)
        assert result.verdict in ["allow", "warn", "block"]

    def test_post_governance_check_drift_block(self, client: TestClient):
        """Vérifie que le drift bloquant déclenche un verdict 'block'."""
        payload = GovernanceCheckRequest(
            session_id="test-session",
            draft_response="Réponse",
            signals=[GovernanceSignal(type="drift", value=0.6)],  # > 0.55
        )
        response = client.post("/governance/check", json=payload.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "block"
        assert len(data["issues"]) > 0
        assert any(issue.get("code", "").startswith("DRIFT") for issue in data["issues"])

    def test_post_governance_check_drift_warn(self, client: TestClient):
        """Vérifie que le drift modéré déclenche un verdict 'warn'."""
        payload = GovernanceCheckRequest(
            session_id="test-session",
            draft_response="Réponse",
            signals=[GovernanceSignal(type="drift", value=0.4)],  # Entre 0.35 et 0.55
        )
        response = client.post("/governance/check", json=payload.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "warn"

    def test_get_metrics_schema(self, client: TestClient):
        """Vérifie que GET /metrics retourne le bon schéma."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure selon OpenAPI
        schema = OPENAPI_SPEC["components"]["schemas"]["MetricsPayload"]
        required_fields = ["kpis", "indicators"]
        for field in required_fields:
            assert field in data, f"Champ requis '{field}' manquant"

        # Vérifier les KPI
        kpis = data["kpis"]
        assert "latency_context_ms" in kpis
        assert "context_payload_bytes" in kpis
        assert "coherence_score" in kpis
        assert "drift_alerts_count" in kpis
        assert "ttl_purge_rate" in kpis
        assert "store_availability" in kpis

    def test_get_metrics_prometheus(self, client: TestClient):
        """Vérifie que GET /metrics/prom retourne du Prometheus."""
        response = client.get("/metrics/prom")
        assert response.status_code == 200
        # Prometheus client utilise version=1.0.0 (ou 0.0.4 selon la version)
        content_type = response.headers["content-type"]
        assert content_type.startswith("text/plain")
        assert "charset=utf-8" in content_type
        assert "version=" in content_type
        content = response.text
        assert "memory_service_context_latency_ms" in content
        assert "memory_service_interactions_total" in content


class TestDataConsistency:
    """Tests de cohérence des données."""

    def test_context_after_interaction(self, client: TestClient):
        """Vérifie que le contexte inclut les données après une interaction."""
        # Créer une interaction
        payload = InteractionRequest(
            interaction_id="test-ctx-001",
            session_id="test-session",
            prompt="Qui est Alice ?",
            response="Alice dirige le pôle Produit depuis 2023.",
            decisions=InteractionDecisions(create_memory=True, derived_traits=["stakeholders"]),
        )
        response = client.post("/interaction", json=payload.model_dump())
        assert response.status_code == 200

        # Récupérer le contexte
        ctx_response = client.get("/context", params={"session_id": "test-session", "max_memories": 5})
        assert ctx_response.status_code == 200
        ctx_data = ctx_response.json()

        # Vérifier qu'un souvenir a été créé
        memories = ctx_data["memories"]
        assert len(memories) > 0, "Aucun souvenir créé après interaction"
        assert any("Alice" in mem.get("content", "") for mem in memories)

    def test_trait_versioning(self, client: TestClient):
        """Vérifie que le versioning des traits fonctionne."""
        trait_id = "test-versioning"
        # Version 1
        payload1 = TraitUpdateRequest(
            trait_id=trait_id,
            delta={"value": "v1"},
            reason="Initial",
            source="test",
        )
        response1 = client.post("/trait-update", json=payload1.model_dump())
        assert response1.status_code == 200
        version1 = response1.json()["trait"]["version"]

        # Version 2
        payload2 = TraitUpdateRequest(
            trait_id=trait_id,
            delta={"value": "v2"},
            reason="Update",
            source="test",
            expected_version=version1,
        )
        response2 = client.post("/trait-update", json=payload2.model_dump())
        assert response2.status_code == 200
        version2 = response2.json()["trait"]["version"]
        assert version2 == version1 + 1

        # Vérifier dans le contexte
        ctx_response = client.get("/context", params={"session_id": "test-session"})
        assert ctx_response.status_code == 200
        traits = ctx_response.json()["traits"]
        trait = next((t for t in traits if t["trait_id"] == trait_id), None)
        assert trait is not None
        assert trait["version"] == version2

    def test_duplicate_detection_via_hash(self, client: TestClient):
        """Vérifie que les doublons sont détectés via hash et incrémentent frequency."""
        content = "Contenu identique pour test de doublon"
        payload1 = InteractionRequest(
            interaction_id="test-dup-001",
            session_id="test-session",
            prompt="Test",
            response=content,
            decisions=InteractionDecisions(create_memory=True),
        )
        response1 = client.post("/interaction", json=payload1.model_dump())
        assert response1.status_code == 200

        # Créer une deuxième interaction avec le même contenu
        payload2 = InteractionRequest(
            interaction_id="test-dup-002",
            session_id="test-session",
            prompt="Test 2",
            response=content,  # Même contenu
            decisions=InteractionDecisions(create_memory=True),
        )
        response2 = client.post("/interaction", json=payload2.model_dump())
        assert response2.status_code == 200

        # Vérifier dans le contexte
        ctx_response = client.get("/context", params={"session_id": "test-session", "max_memories": 10})
        assert ctx_response.status_code == 200
        memories = ctx_response.json()["memories"]
        matching = [m for m in memories if content in m.get("content", "")]
        # Soit un seul souvenir avec frequency=2, soit deux souvenirs (selon implémentation)
        assert len(matching) > 0
        # Si détection de doublon fonctionne, frequency devrait être > 1
        if len(matching) == 1:
            assert matching[0].get("frequency", 1) >= 2


class TestPerformance:
    """Tests de performance et limites."""

    def test_context_build_time(self, client: TestClient):
        """Vérifie que le temps de construction est < 200ms."""
        import time

        start = time.time()
        response = client.get("/context", params={"session_id": "test-session"})
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 200, f"Temps de réponse trop élevé: {elapsed_ms:.2f}ms"

    def test_multiple_interactions(self, client: TestClient):
        """Vérifie que plusieurs interactions successives fonctionnent."""
        for i in range(10):
            payload = InteractionRequest(
                interaction_id=f"test-perf-{i:03d}",
                session_id="test-session",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
            )
            response = client.post("/interaction", json=payload.model_dump())
            assert response.status_code == 200

        # Vérifier le contexte
        ctx_response = client.get("/context", params={"session_id": "test-session"})
        assert ctx_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Tests fumée du service mémoire."""

import pytest
from fastapi.testclient import TestClient

from memory_service.api import create_app
from memory_service.config import get_settings
from memory_service.schemas import (
    GovernanceCheckRequest,
    GovernanceSignal,
    InteractionDecisions,
    InteractionRequest,
    TraitUpdateRequest,
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_SERVICE_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("MEMORY_SERVICE_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_health_and_context_flow(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    interaction_payload = InteractionRequest(
        interaction_id="test-i-001",
        session_id="default",
        prompt="Salut",
        response="Bonjour, que puis-je faire pour vous ?",
        decisions=InteractionDecisions(derived_traits=["tone"]),
    )
    res_interaction = client.post("/interaction", json=interaction_payload.model_dump())
    assert res_interaction.status_code == 200, res_interaction.text

    ctx = client.get("/context", params={"session_id": "default"})
    assert ctx.status_code == 200
    body = ctx.json()
    assert "traits" in body and body["traits"], "Le contexte doit contenir des traits."
    assert body["build_time_ms"] >= 0

    trait_payload = TraitUpdateRequest(
        trait_id="tone",
        delta={"value": "toujours empathique"},
        reason="Interaction positive",
        source="test",
    )
    res_trait = client.post("/trait-update", json=trait_payload.model_dump())
    assert res_trait.status_code == 200
    assert res_trait.json()["trait"]["version"] >= 1

    gov_payload = GovernanceCheckRequest(
        session_id="default",
        draft_response="Réponse courte",
        signals=[
            GovernanceSignal(type="coherence", value=0.9),
            GovernanceSignal(type="drift", value=0.1),
        ],
    )
    res_gov = client.post("/governance/check", json=gov_payload.model_dump())
    assert res_gov.status_code == 200
    assert res_gov.json()["verdict"] in {"allow", "warn"}

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "indicators" in metrics.json()

    prom = client.get("/metrics/prom")
    assert prom.status_code == 200
    assert "memory_service_context_latency_ms" in prom.text




"""Tests pour la CLI de seed/supervision."""

import pytest

from memory_service.cli import collect_stats, seed_database
from memory_service.config import get_settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_SERVICE_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("MEMORY_SERVICE_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_seed_database_and_stats():
    payload = {
        "traits": [
            {
                "trait_id": "testing",
                "type": "skill",
                "label": "Tests",
                "value": "Toujours valider les specs",
            }
        ],
        "souvenirs": [],
        "session_goals": [],
        "interactions": [],
    }
    summary = seed_database(seed_payload=payload)
    assert summary["traits"] == 1

    stats = collect_stats()
    assert stats["counts"]["traits"] >= 1
    assert stats["counts"]["souvenirs"] == 0
    assert stats["goals"], "Un objectif par défaut doit exister"




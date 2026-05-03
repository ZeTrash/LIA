"""Tests pour GeminiAdapter."""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from support import GeminiAdapter, SupportConfig


@pytest.fixture
def config():
    """Crée une configuration de test."""
    return SupportConfig(
        gemini_api_key="test_key",
        gemini_model="gemini-pro",
        enable_learning=True
    )


@pytest.fixture
def adapter(config):
    """Crée un adaptateur Gemini pour les tests."""
    return GeminiAdapter(config)


def test_is_available_with_key(adapter):
    """Test que l'adaptateur est disponible avec une clé API."""
    assert adapter.is_available() is True


def test_is_available_without_key():
    """Test que l'adaptateur n'est pas disponible sans clé API."""
    config = SupportConfig(gemini_api_key=None)
    adapter = GeminiAdapter(config)
    assert adapter.is_available() is False


def test_is_available_with_placeholder_key():
    """Test que l'adaptateur n'est pas disponible avec la clé placeholder."""
    config = SupportConfig(gemini_api_key="YOUR_GEMINI_API_KEY_HERE")
    adapter = GeminiAdapter(config)
    assert adapter.is_available() is False


def test_build_prompt_simple(adapter):
    """Test de construction de prompt simple."""
    prompt = adapter._build_prompt("Qu'est-ce que l'IA ?")
    assert "Qu'est-ce que l'IA ?" in prompt


def test_build_prompt_with_context(adapter):
    """Test de construction de prompt avec contexte."""
    context = {
        "traits": [{"label": "curiosité", "value": "très curieux"}],
        "memories": [{"content": "Aime apprendre"}]
    }
    prompt = adapter._build_prompt("Qu'est-ce que l'IA ?", context)
    assert "Qu'est-ce que l'IA ?" in prompt
    assert "curiosité" in prompt or "curieux" in prompt


def test_reset_query_count(adapter):
    """Test de réinitialisation du compteur de requêtes."""
    adapter._query_count = 5
    adapter.reset_query_count()
    assert adapter._query_count == 0


@pytest.mark.asyncio
async def test_query_without_api_key():
    """Test que query échoue sans clé API."""
    config = SupportConfig(gemini_api_key=None)
    adapter = GeminiAdapter(config)
    
    with pytest.raises(RuntimeError, match="Gemini API non disponible"):
        await adapter.query("Test question")


@pytest.mark.asyncio
async def test_query_limit_reached(adapter):
    """Test que query échoue si la limite est atteinte."""
    adapter._query_count = adapter.config.max_queries_per_session
    
    with pytest.raises(RuntimeError, match="Limite de requêtes atteinte"):
        await adapter.query("Test question")


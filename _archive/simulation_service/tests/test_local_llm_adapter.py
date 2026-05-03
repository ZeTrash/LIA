"""Tests pour LocalLLMAdapter."""

import sys
import time
from pathlib import Path

import pytest

# Ajouter le répertoire src au PYTHONPATH
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from simulation_service.adapters import LocalLLMAdapter, AgentConfig


@pytest.fixture
def local_llm_config():
    """Configuration pour LocalLLMAdapter."""
    return AgentConfig(
        agent_id="test-local",
        agent_type="llm-local"
    )


def test_local_llm_adapter_creation(local_llm_config):
    """Test création LocalLLMAdapter."""
    adapter = LocalLLMAdapter(local_llm_config)
    assert adapter is not None
    assert adapter.model_name == "gpt2" or adapter.model_name == "distilgpt2"
    assert adapter.device in ["cpu", "cuda"]


@pytest.mark.asyncio
async def test_local_llm_generate(local_llm_config):
    """Test génération de réponse."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    response = await adapter.send_message("Bonjour")
    assert response is not None
    assert len(response) > 0


@pytest.mark.asyncio
async def test_local_llm_with_context(local_llm_config):
    """Test génération avec contexte mémoire."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    context = {
        "traits": [
            {"trait_id": "curiosity", "label": "Curiosité", "value": "0.85"}
        ],
        "memories": [
            {"content": "LIA aime la philosophie"}
        ]
    }
    
    response = await adapter.send_message(
        "Qu'est-ce que tu penses ?",
        context=context
    )
    assert response is not None


def test_build_prompt(local_llm_config):
    """Test construction du prompt."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    context = {
        "traits": [
            {"label": "Curiosité", "value": "élevée"}
        ],
        "memories": [
            {"content": "Souvenir test"}
        ],
        "session_goals": [
            {"description": "Objectif test"}
        ]
    }
    
    # Test avec ordre corrigé : build_prompt(message, context)
    prompt = adapter.build_prompt("Bonjour", context)
    assert "[Personnalité LIA]" in prompt
    assert "[Souvenirs pertinents]" in prompt
    assert "[Objectifs de session]" in prompt
    assert "[Conversation]" in prompt
    assert "Bonjour" in prompt
    assert "Curiosité" in prompt


def test_get_memory_usage_mb(local_llm_config):
    """Test de récupération de l'utilisation mémoire."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    memory_mb = adapter.get_memory_usage_mb()
    assert isinstance(memory_mb, (int, float))
    assert memory_mb >= 0


def test_unload_model(local_llm_config):
    """Test de déchargement du modèle."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    # Vérifier que le modèle est chargé
    assert adapter.model is not None
    
    # Décharger
    adapter.unload_model()
    
    # Vérifier que le modèle est déchargé
    assert adapter.model is None


@pytest.mark.asyncio
async def test_performance_latency(local_llm_config):
    """Test de performance (latence)."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    start_time = time.time()
    response = await adapter.send_message("Test rapide")
    latency = time.time() - start_time
    
    assert response is not None
    # Seuil ajusté pour CPU (peut être plus lent que GPU)
    assert latency < 15.0  # Moins de 15 secondes pour une réponse courte sur CPU
    print(f"Latence: {latency:.2f}s")


def test_performance_memory(local_llm_config):
    """Test de performance (mémoire)."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    memory_mb = adapter.get_memory_usage_mb()
    
    # Vérifier que la mémoire est raisonnable
    # Note: GPT-2 peut utiliser jusqu'à ~1.5GB sur CPU selon la configuration
    # Seuil ajusté pour être plus réaliste
    assert memory_mb < 2000  # Seuil large pour éviter les faux positifs
    print(f"Mémoire utilisée: {memory_mb:.2f} MB")


@pytest.mark.asyncio
async def test_handshake(local_llm_config):
    """Test du handshake."""
    adapter = LocalLLMAdapter(local_llm_config)
    
    handshake = await adapter.perform_handshake()
    assert handshake["agent_id"] == "test-local"
    assert handshake["agent_type"] == "llm-local"
    assert "model_name" in handshake
    assert "device" in handshake
    assert "memory_usage_mb" in handshake
    assert "quantization_bits" in handshake



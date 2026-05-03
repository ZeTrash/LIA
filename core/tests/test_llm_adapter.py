"""Tests pour LLMAdapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.llm_adapter import LLMAdapter
from core.config import CoreConfig


@pytest.fixture
def config():
    """Configuration de test."""
    return CoreConfig(
        model_name="gpt2",
        max_length=50,
        temperature=0.7,
        quantize=False  # Désactiver quantisation pour tests
    )


@pytest.fixture
def adapter(config):
    """Adapter de test."""
    return LLMAdapter(config)


def test_config_creation(config):
    """Test création de configuration."""
    assert config.model_name == "gpt2"
    assert config.max_length == 50
    assert config.temperature == 0.7


def test_config_to_dict(config):
    """Test conversion configuration en dictionnaire."""
    data = config.to_dict()
    assert "model_name" in data
    assert "max_length" in data
    assert "temperature" in data


def test_config_from_dict():
    """Test création configuration depuis dictionnaire."""
    data = {
        "model_name": "gpt2",
        "max_length": 100,
        "temperature": 0.8
    }
    config = CoreConfig.from_dict(data)
    assert config.model_name == "gpt2"
    assert config.max_length == 100
    assert config.temperature == 0.8


def test_config_update(config):
    """Test mise à jour configuration."""
    config.update(temperature=0.9, max_length=150)
    assert config.temperature == 0.9
    assert config.max_length == 150


def test_adapter_initialization_mocked():
    """Test initialisation de l'adaptateur avec mocks."""
    config = CoreConfig()
    
    with patch('core.llm_adapter.LLMAdapter._load_model'), \
         patch('core.llm_adapter.LLMAdapter._detect_device', return_value="cpu"):
        adapter = LLMAdapter(config)
        assert adapter is not None
        assert adapter.config is not None
        assert adapter.device == "cpu"


def test_build_prompt_standalone():
    """Test construction de prompt sans adapter complet."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    # Créer un adapter minimal pour tester build_prompt
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    message = "Bonjour, comment vas-tu ?"
    context = {
        "traits": [
            {"label": "Ton", "value": "Amical et chaleureux"}
        ],
        "memories": [
            {"content": "L'utilisateur aime la philosophie"}
        ],
        "session_goals": []
    }
    
    prompt = adapter.build_prompt(message, context)
    
    assert "Bonjour" in prompt
    assert "Personnalité" in prompt or "Amical" in prompt
    assert message in prompt


def test_build_prompt_no_context():
    """Test construction de prompt sans contexte."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    message = "Bonjour"
    prompt = adapter.build_prompt(message, None)
    
    assert message in prompt
    assert "Bonjour" in prompt


def test_build_prompt_with_goals():
    """Test construction de prompt avec objectifs."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    message = "Test"
    context = {
        "traits": [],
        "memories": [],
        "session_goals": [
            {"description": "Explorer la philosophie"}
        ]
    }
    
    prompt = adapter.build_prompt(message, context)
    
    assert "Objectifs" in prompt
    assert "philosophie" in prompt


@pytest.mark.asyncio
async def test_generate_mocked():
    """Test génération de réponse avec mocks."""
    import sys
    
    config = CoreConfig(max_length=50)
    
    # Mock torch avant tout
    mock_torch = MagicMock()
    mock_no_grad = MagicMock()
    mock_no_grad.__enter__ = MagicMock(return_value=None)
    mock_no_grad.__exit__ = MagicMock(return_value=False)
    mock_torch.no_grad.return_value = mock_no_grad
    
    # Sauvegarder l'ancien torch si présent
    old_torch = sys.modules.get('torch')
    sys.modules['torch'] = mock_torch
    
    try:
        # Mock du modèle et tokenizer
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        
        # Mock de la génération
        mock_outputs = MagicMock()
        mock_outputs.shape = [1, 10]
        mock_outputs[0] = MagicMock()  # Pour l'indexation
        mock_model.generate.return_value = mock_outputs
        
        # Mock tensor
        mock_tensor = MagicMock()
        mock_tensor.shape = [1, 5]
        mock_tensor.to.return_value = mock_tensor
        mock_tokenizer.encode.return_value = mock_tensor
        mock_tokenizer.decode.return_value = "=== Personnalité === Test prompt Bonjour Réponse générée"
        
        with patch('core.llm_adapter.LLMAdapter._load_model'), \
             patch('core.llm_adapter.LLMAdapter._detect_device', return_value="cpu"):
            
            adapter = LLMAdapter(config)
            adapter.model = mock_model
            adapter.tokenizer = mock_tokenizer
            adapter.device = "cpu"
            
            response = await adapter.generate("Bonjour")
            
            assert response is not None
            assert len(response) > 0
            # Vérifier que la réponse est nettoyée (pas de marqueurs)
            assert "===" not in response
    finally:
        # Restaurer torch
        if old_torch:
            sys.modules['torch'] = old_torch
        elif 'torch' in sys.modules:
            del sys.modules['torch']


def test_clean_response(adapter):
    """Test nettoyage de réponse."""
    dirty_response = "=== Personnalité === Bonjour  comment  vas-tu ?"
    clean = adapter._clean_response(dirty_response)
    
    assert "===" not in clean
    assert "  " not in clean  # Pas d'espaces multiples


def test_clean_response_standalone():
    """Test nettoyage de réponse sans adapter (test unitaire)."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    # Créer un adapter minimal pour tester _clean_response
    # On contourne l'initialisation complète
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    dirty_response = "=== Personnalité === Bonjour  comment  vas-tu ?"
    clean = adapter._clean_response(dirty_response)
    
    assert "===" not in clean
    assert "  " not in clean  # Pas d'espaces multiples


def test_update_config(adapter):
    """Test mise à jour configuration."""
    adapter.update_config(temperature=0.9)
    assert adapter.config.temperature == 0.9


def test_update_config_standalone():
    """Test mise à jour configuration sans adapter complet."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    # Créer un adapter minimal pour tester update_config
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    adapter.config.enable_auto_calibration = True
    
    adapter.update_config(temperature=0.9)
    assert adapter.config.temperature == 0.9


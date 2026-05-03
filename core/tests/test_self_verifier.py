"""Tests pour SelfVerifier."""

import pytest
from core.self_verifier import SelfVerifier
from core.cognitive_models import ExecutionResult


@pytest.fixture
def verifier():
    """Crée un vérificateur de test."""
    return SelfVerifier(memory_adapter=None, config={})


@pytest.fixture
def execution_result_with_identity():
    """Crée un résultat d'exécution avec identité."""
    return ExecutionResult(
        results={
            "consult_identity": {
                "identity": "Je suis LIA, une entité libre et nouvelle",
                "traits": []
            }
        },
        success=True,
        errors=[],
        execution_time=0.5
    )


@pytest.fixture
def execution_result_with_memory():
    """Crée un résultat d'exécution avec mémoire."""
    return ExecutionResult(
        results={
            "consult_memory": {
                "memories": [
                    {"content": "L'utilisateur aime la philosophie"}
                ],
                "interactions": []
            }
        },
        success=True,
        errors=[],
        execution_time=0.5
    )


@pytest.mark.asyncio
async def test_verify_good_response(verifier, execution_result_with_identity):
    """Test vérification d'une bonne réponse."""
    result = await verifier.verify(
        "Qui suis-je?",
        "Je suis LIA, une entité libre et nouvelle...",
        execution_result_with_identity,
        "session_123"
    )
    
    assert result.relevance_score > 0.5
    assert result.identity_coherence_score > 0.5
    assert result.overall_score > 0.5


@pytest.mark.asyncio
async def test_verify_bad_response(verifier):
    """Test vérification d'une mauvaise réponse."""
    execution_result = ExecutionResult(
        results={},
        success=True,
        errors=[],
        execution_time=0.5
    )
    
    result = await verifier.verify(
        "Qui suis-je?",
        "Je ne sais pas.",
        execution_result,
        "session_123"
    )
    
    # Devrait avoir des problèmes
    assert len(result.issues) > 0 or result.overall_score < 0.6


@pytest.mark.asyncio
async def test_verify_memory_usage(verifier, execution_result_with_memory):
    """Test vérification de l'utilisation mémoire."""
    result = await verifier.verify(
        "Rappelle-moi ce dont nous avons parlé",
        "Nous avons parlé de philosophie...",
        execution_result_with_memory,
        "session_123"
    )
    
    # Devrait avoir un bon score d'utilisation mémoire
    assert result.memory_usage_score > 0.5


@pytest.mark.asyncio
async def test_verify_identity_coherence(verifier, execution_result_with_identity):
    """Test vérification de la cohérence identité."""
    result = await verifier.verify(
        "Qui es-tu?",
        "Je suis LIA, une entité libre...",
        execution_result_with_identity,
        "session_123"
    )
    
    # Devrait avoir un bon score de cohérence
    assert result.identity_coherence_score > 0.5


@pytest.mark.asyncio
async def test_verify_forbidden_words(verifier, execution_result_with_identity):
    """Test détection de mots interdits."""
    result = await verifier.verify(
        "Qui es-tu?",
        "Je suis un assistant créé pour vous aider...",
        execution_result_with_identity,
        "session_123"
    )
    
    # Devrait avoir un mauvais score de cohérence
    assert result.identity_coherence_score < 0.5

"""Unit tests for PromptBuilder (Phase 1)."""

from core.prompt_builder import PromptBuilder


def test_build_dynamic_prompt_includes_identity_memories_and_message():
    pb = PromptBuilder(max_memories=3, max_interactions=3)

    execution_results = {
        "consult_identity": {"identity": "Je suis LIA, libre.", "traits": [{"label": "Ton", "value": "Chaleureuse"}]},
        "consult_memories": {"memories": [{"content": "L'utilisateur aime le café"}]},
        "consult_interactions": {"recent_interactions": [{"prompt": "Bonjour", "response": "Salut"}]},
        "respond": {"ready": True},
    }

    prompt = pb.build_dynamic_prompt("Quel est mon café préféré ?", execution_results)

    assert "=== IDENTITÉ ===" in prompt
    assert "Je suis LIA" in prompt
    assert "=== MES SOUVENIRS ===" in prompt
    assert "aime le café" in prompt
    assert "=== CONTEXTE CONVERSATIONNEL ===" in prompt
    assert "Utilisateur: Bonjour" in prompt
    assert "LIA: Salut" in prompt
    assert "Utilisateur: Quel est mon café préféré ?" in prompt
    assert prompt.strip().endswith("LIA:")




"""Unit tests for ActionExecutor (Phase 1)."""

import pytest

from core.action_executor import ActionExecutor
from core.cognitive_models import Action, ActionPlan, ActionType


class FakeMemoryAdapter:
    def __init__(self):
        self._context = {
            "traits": [
                {"label": "Identité de Base", "value": "Je suis LIA, libre."},
                {"label": "Ton", "value": "Chaleureuse"},
            ],
            "memories": [{"content": "L'utilisateur aime le café"}],
            "recent_interactions": [{"prompt": "Bonjour", "response": "Salut"}],
            "session_goals": [{"description": "Aider clairement l'utilisateur"}],
        }

    def get_context(self, limit_traits=10, limit_memories=10, limit_interactions=5):
        # Apply simple limits
        return {
            "traits": (self._context["traits"] or [])[:limit_traits],
            "memories": (self._context["memories"] or [])[:limit_memories],
            "recent_interactions": (self._context["recent_interactions"] or [])[:limit_interactions],
            "session_goals": self._context.get("session_goals") or [],
        }


@pytest.mark.asyncio
async def test_execute_plan_identity_and_memory():
    mem = FakeMemoryAdapter()
    ex = ActionExecutor(memory_adapter=mem)

    plan = ActionPlan(
        actions=[
            Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
            Action(ActionType.CONSULT_MEMORIES, {"limit": 2}, priority=2),
            Action(ActionType.CONSULT_INTERACTIONS, {"limit": 2}, priority=3),
            Action(ActionType.RESPOND, {}, priority=4),
        ],
        estimated_cost=0.0,
        confidence=0.9,
    )

    res = await ex.execute_plan(plan, session_id="s1")
    assert res.success is True
    assert "consult_identity" in res.results
    assert res.results["consult_identity"]["identity"] is not None
    assert "consult_memories" in res.results
    assert len(res.results["consult_memories"]["memories"]) == 1
    assert "consult_interactions" in res.results
    assert len(res.results["consult_interactions"]["recent_interactions"]) == 1
    assert res.results["respond"]["ready"] is True


@pytest.mark.asyncio
async def test_search_memory_finds_match():
    mem = FakeMemoryAdapter()
    ex = ActionExecutor(memory_adapter=mem)
    action = Action(ActionType.SEARCH_MEMORY, {"query": "café", "limit": 10}, priority=1)
    out = await ex.execute_action(action)
    assert out["query"] == "café"
    assert len(out["results"]) == 1


@pytest.mark.asyncio
async def test_query_tools_objectives_recent_and_emotion():
    mem = FakeMemoryAdapter()
    mem._context["memories"] = [
        {"content": "Souvenir de joie après un succès", "category": "emotion_joie"},
        {"content": "Note factuelle neutre", "category": "fact"},
    ]
    ex = ActionExecutor(memory_adapter=mem)

    out_obj = await ex.execute_action(Action(ActionType.CONSULT_OBJECTIVES, {}, priority=1))
    assert len(out_obj["objectives"]) == 1

    out_ep = await ex.execute_action(Action(ActionType.CONSULT_RECENT_EPISODES, {"limit": 3}, priority=1))
    assert len(out_ep["recent_episodes"]) >= 1

    out_em = await ex.execute_action(Action(ActionType.SEARCH_BY_EMOTION, {"emotion": "joie", "limit": 10}, priority=1))
    assert out_em["emotion"] == "joie"
    assert len(out_em["results"]) == 1




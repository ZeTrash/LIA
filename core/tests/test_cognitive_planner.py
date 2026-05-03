"""Unit tests for CognitivePlanner (Phase 1)."""

import pytest

from core.cognitive_planner import CognitivePlanner, PlannerConfig
from core.cognitive_models import ActionType


@pytest.mark.asyncio
async def test_plan_identity_request_includes_identity_then_respond():
    planner = CognitivePlanner(config=PlannerConfig())
    plan = await planner.plan("Qui es-tu ?")

    types = [a.type for a in plan.sorted_actions()]
    assert ActionType.CONSULT_IDENTITY in types
    assert types[-1] == ActionType.RESPOND


@pytest.mark.asyncio
async def test_plan_memory_request_includes_interactions_and_memories():
    planner = CognitivePlanner(config=PlannerConfig(default_interactions_limit=7, default_memories_limit=9))
    plan = await planner.plan("Rappelle-moi ce dont on a parlé hier.")

    actions = plan.sorted_actions()
    types = [a.type for a in actions]
    assert ActionType.CONSULT_INTERACTIONS in types
    assert ActionType.CONSULT_MEMORIES in types
    assert actions[-1].type == ActionType.RESPOND


@pytest.mark.asyncio
async def test_plan_external_intent_adds_query_external_optional():
    planner = CognitivePlanner()
    plan = await planner.plan("Peux-tu rechercher une source à jour sur ce sujet ?")

    actions = plan.sorted_actions()
    external = [a for a in actions if a.type == ActionType.QUERY_EXTERNAL]
    assert len(external) == 1
    assert external[0].required is False
    assert actions[-1].type == ActionType.RESPOND




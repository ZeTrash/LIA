import pytest

from core.cognitive_models import Action, ActionPlan, ActionType, ExecutionResult
from core.query_brain import QueryBrain, QueryBrainInput


class _Planner:
    def __init__(self, max_tool_calls=2):
        self.config = {"max_tool_calls": max_tool_calls}

    async def plan(self, user_message: str, session_id: str = "default"):
        return ActionPlan(
            actions=[
                Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
                Action(ActionType.CONSULT_OBJECTIVES, {}, priority=2),
                Action(ActionType.CONSULT_RECENT_EPISODES, {"limit": 5}, priority=3),
                Action(ActionType.SEARCH_BY_EMOTION, {"emotion": "joie", "limit": 10}, priority=4),
                Action(ActionType.RESPOND, {}, priority=5),
            ],
            confidence=0.9,
        )

    def _analyze_request(self, user_message: str):
        return type(
            "A",
            (),
            {"needs_identity": True, "needs_memory": True},
        )()


class _Executor:
    async def execute_plan(self, plan: ActionPlan, session_id: str = "default"):
        return ExecutionResult(
            results={"plan_actions": [a.type.value for a in plan.sorted_actions()]},
            success=True,
            errors=[],
            execution_time=0.0,
        )


@pytest.mark.asyncio
async def test_query_brain_applies_max_tool_calls_budget():
    qb = QueryBrain(planner=_Planner(max_tool_calls=2), executor=_Executor())
    out = await qb.run(QueryBrainInput(user_message="test", session_id="s1"))
    actions = [a.type for a in out.plan.sorted_actions()]
    # 2 outils max + respond
    assert actions.count(ActionType.RESPOND) == 1
    assert len([a for a in actions if a != ActionType.RESPOND]) == 2

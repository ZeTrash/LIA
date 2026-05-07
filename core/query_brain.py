"""QueryBrain: récupération autonome de contexte via tools (planner + executor).

Objectif:
- Remplacer la boucle de menus itératifs quand on veut un chemin autonome.
- S'appuyer sur les composants existants: CognitivePlanner + ActionExecutor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .cognitive_models import ActionPlan, ExecutionResult
from .cognitive_models import Action, ActionType


@dataclass(frozen=True)
class QueryBrainInput:
    user_message: str
    session_id: str
    base_results: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class QueryBrainOutput:
    plan: ActionPlan
    execution_result: ExecutionResult
    autonomy_mode: str
    stop_reason: str
    plan_confidence: float


class QueryBrain:
    """Orchestrateur de récupération de contexte (MVP)."""

    def __init__(self, planner: Any, executor: Any, autonomy_mode: str = "auto_with_audit"):
        self.planner = planner
        self.executor = executor
        self.autonomy_mode = autonomy_mode

    async def run(self, qb_in: QueryBrainInput) -> QueryBrainOutput:
        if not self.planner or not self.executor:
            raise RuntimeError("QueryBrain requires planner and executor")

        plan = await self.planner.plan(qb_in.user_message, session_id=qb_in.session_id)
        plan = self._apply_tool_budget(plan)
        execution_result = await self.executor.execute_plan(plan, session_id=qb_in.session_id)

        # Merge base_results into results (non-destructive)
        if qb_in.base_results:
            merged = dict(qb_in.base_results)
            merged.update(execution_result.results or {})
            execution_result = ExecutionResult(
                results=merged,
                success=execution_result.success,
                errors=list(execution_result.errors or []),
                execution_time=execution_result.execution_time,
            )

        return QueryBrainOutput(
            plan=plan,
            execution_result=execution_result,
            autonomy_mode=self.autonomy_mode,
            stop_reason="auto_plan",
            plan_confidence=float(getattr(plan, "confidence", 0.0) or 0.0),
        )

    async def replan_safe_minimal(self, qb_in: QueryBrainInput) -> QueryBrainOutput:
        """Replan autonome 'safe minimal' sans menus fixes.

        But: produire un plan utile même si la confiance du planner est faible.
        """
        if not self.planner or not self.executor:
            raise RuntimeError("QueryBrain requires planner and executor")

        analysis = None
        try:
            analysis = getattr(self.planner, "_analyze_request")(qb_in.user_message)
        except Exception:
            analysis = None

        actions = []
        pr = 1
        # Minimal: identité et mémoire si signalés
        if analysis and getattr(analysis, "needs_identity", False):
            actions.append(Action(ActionType.CONSULT_IDENTITY, {}, priority=pr))
            pr += 1
        if analysis and getattr(analysis, "needs_memory", False):
            actions.append(Action(ActionType.CONSULT_INTERACTIONS, {"limit": 5}, priority=pr))
            pr += 1
            actions.append(Action(ActionType.CONSULT_MEMORIES, {"limit": 5}, priority=pr))
            pr += 1
        # Toujours finir par RESPOND
        actions.append(Action(ActionType.RESPOND, {}, priority=pr))

        plan = ActionPlan(actions=actions, estimated_cost=10.0, confidence=0.65)
        plan = self._apply_tool_budget(plan)
        execution_result = await self.executor.execute_plan(plan, session_id=qb_in.session_id)

        if qb_in.base_results:
            merged = dict(qb_in.base_results)
            merged.update(execution_result.results or {})
            execution_result = ExecutionResult(
                results=merged,
                success=execution_result.success,
                errors=list(execution_result.errors or []),
                execution_time=execution_result.execution_time,
            )

        return QueryBrainOutput(
            plan=plan,
            execution_result=execution_result,
            autonomy_mode=self.autonomy_mode,
            stop_reason="replan_safe_minimal",
            plan_confidence=float(getattr(plan, "confidence", 0.0) or 0.0),
        )

    def _apply_tool_budget(self, plan: ActionPlan) -> ActionPlan:
        planner_config = getattr(self.planner, "config", None)
        if isinstance(planner_config, dict):
            max_tool_calls = int(planner_config.get("max_tool_calls", 5))
        else:
            max_tool_calls = int(getattr(planner_config, "max_tool_calls", 5))
        max_tool_calls = max(1, max_tool_calls)

        sorted_actions = plan.sorted_actions()
        non_respond = [a for a in sorted_actions if a.type != ActionType.RESPOND]
        respond = next((a for a in sorted_actions if a.type == ActionType.RESPOND), Action(ActionType.RESPOND, {}, priority=0))

        if len(non_respond) <= max_tool_calls:
            return plan

        trimmed = non_respond[:max_tool_calls] + [respond]
        normalized = []
        pr = 1
        for a in trimmed:
            normalized.append(Action(a.type, dict(a.parameters or {}), priority=pr, required=a.required))
            pr += 1
        confidence = max(0.0, float(getattr(plan, "confidence", 0.5) or 0.5) - 0.05)
        return ActionPlan(actions=normalized, estimated_cost=plan.estimated_cost, confidence=confidence)


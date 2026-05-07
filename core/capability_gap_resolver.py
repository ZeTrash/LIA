"""Résolution des capacités manquantes via CodeBrain (MVP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional


CodeActionCallback = Callable[[str], Awaitable[Dict[str, Any]]]


@dataclass
class CapabilityResolution:
    decision: str
    success: bool
    details: Dict[str, Any]


class CapabilityGapResolver:
    """Décide quoi faire quand une capacité manque."""

    def __init__(self, code_action_callback: Optional[CodeActionCallback] = None):
        self.code_action_callback = code_action_callback

    async def resolve_for_desire(self, desire_name: str) -> CapabilityResolution:
        # Heuristique MVP: les désirs de création/amélioration passent par CodeBrain.
        if "CodeBrain" not in desire_name and "module" not in desire_name.lower():
            return CapabilityResolution(
                decision="no_gap",
                success=True,
                details={"reason": "desire does not require new capability"},
            )

        if self.code_action_callback is None:
            return CapabilityResolution(
                decision="blocked",
                success=False,
                details={"reason": "code_action_callback unavailable"},
            )

        spec = "créer ou améliorer une capacité requise par le désir autonome courant"
        result = await self.code_action_callback(spec)
        return CapabilityResolution(
            decision="create_capability",
            success=bool(result.get("success", False)),
            details=result,
        )


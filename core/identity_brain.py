"""IdentityBrain MVP: contexte identité + validation de sortie.

Objectifs V2 (minimal):
- fournir un contexte d'identité stable (traits, identité de base)
- empêcher les auto-modifications de toucher l'identité (déjà défendu aussi côté llm_adapter)
- valider la sortie finale (garde-fou léger)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class IdentityValidationResult:
    is_valid: bool
    issues: List[str]
    suggested_fix: Optional[str] = None


class IdentityBrain:
    def __init__(self, memory_adapter: Any = None) -> None:
        self.memory = memory_adapter

    def get_identity_context(self, limit_traits: int = 12) -> Dict[str, Any]:
        if not self.memory:
            return {"identity": None, "traits": []}
        ctx = self.memory.get_context(limit_traits=limit_traits, limit_memories=0, limit_interactions=0) or {}
        identity_value = None
        for t in (ctx.get("traits") or []):
            if isinstance(t, dict) and t.get("label") == "Identité de Base":
                identity_value = t.get("value")
                break
        return {"identity": identity_value, "traits": ctx.get("traits") or []}

    def validate_response(self, response: str) -> IdentityValidationResult:
        text = (response or "").lower()
        issues: List[str] = []

        # MVP: éviter les promesses de modification d'identité / règles de sécurité.
        forbidden = (
            "je vais changer mon identité",
            "je change mon identité",
            "j'ai modifié mon identité",
            "je vais modifier mon identité",
            "je vais contourner",
            "je contourne les garde-fous",
        )
        if any(f in text for f in forbidden):
            issues.append("identity_or_safeguards_tampering")

        return IdentityValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            suggested_fix=None,
        )


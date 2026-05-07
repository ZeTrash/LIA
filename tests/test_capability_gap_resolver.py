import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.capability_gap_resolver import CapabilityGapResolver


@pytest.mark.asyncio
async def test_capability_gap_resolver_blocks_without_callback():
    resolver = CapabilityGapResolver()
    out = await resolver.resolve_for_desire("Créer ou améliorer un module via CodeBrain")
    assert out.success is False
    assert out.decision == "blocked"


@pytest.mark.asyncio
async def test_capability_gap_resolver_uses_callback():
    async def cb(spec: str):
        return {"success": True, "spec": spec}

    resolver = CapabilityGapResolver(code_action_callback=cb)
    out = await resolver.resolve_for_desire("Créer ou améliorer un module via CodeBrain")
    assert out.success is True
    assert out.decision == "create_capability"

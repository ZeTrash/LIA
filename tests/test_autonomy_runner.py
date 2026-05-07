import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomy.runner import AutonomyRunner  # noqa: E402


@pytest.mark.asyncio
async def test_autonomy_runner_start_tick_stop(tmp_path: Path):
    events = []

    async def on_event(ev):
        events.append(ev)

    runner = AutonomyRunner(system_events_log_path=tmp_path / "events.jsonl", on_event=on_event)

    async def tick_fn(run_id: str, step: int, prompt: str):
        assert run_id.startswith("autonomy-")
        assert step >= 1
        assert "OBJECTIF_GLOBAL" in prompt
        return {"lia_response": f"ok step {step}"}

    st = await runner.start(objective="Tester la boucle autonome", tick_fn=tick_fn, interval_s=0.2, max_steps=3)
    assert st.running is True

    # Laisser quelques ticks s'exécuter
    await asyncio.sleep(0.9)
    st2 = runner.status()
    assert st2.step >= 1

    await runner.stop(reason="test_stop")
    st3 = runner.status()
    assert st3.running is False

    # Vérifier qu'on a bien émis des événements
    types = [e.get("type") for e in events]
    assert "autonomy_started" in types
    assert "autonomy_tick" in types

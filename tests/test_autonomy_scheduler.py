import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.autonomy_brain import AutonomyBrain
from core.autonomy_scheduler import AutonomyScheduler
from memory_service.autonomy_store import AutonomyStore


@pytest.mark.asyncio
async def test_autonomy_scheduler_cycle_and_start_stop(tmp_path: Path):
    store = AutonomyStore(db_path=str(tmp_path / "autonomy_scheduler.db"))
    brain = AutonomyBrain(store=store)
    scheduler = AutonomyScheduler(brain=brain)

    payload = await scheduler.run_single_cycle()
    assert payload["type"] == "autonomy_cycle"
    assert scheduler.cycles_completed >= 1

    st = await scheduler.start(interval_seconds=0.5)
    assert st.running is True
    await asyncio.sleep(1.2)
    st2 = await scheduler.stop()
    assert st2.running is False
    assert scheduler.cycles_completed >= 2

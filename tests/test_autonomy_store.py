import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.autonomy_models import AutonomyState, Desire, Dream, Gauge, Trait
from memory_service.autonomy_store import AutonomyStore


def test_autonomy_store_seed_and_cycle(tmp_path: Path):
    db_path = tmp_path / "autonomy.db"
    store = AutonomyStore(db_path=str(db_path))
    store.ensure_seed()
    state = store.load_state()
    assert len(state.gauges) >= 4
    assert len(state.traits) >= 3

    store.append_cycle({"type": "autonomy_cycle", "ok": True})
    recent = store.list_recent_cycles(limit=5)
    assert len(recent) == 1
    assert recent[0]["payload"]["type"] == "autonomy_cycle"


def test_autonomy_store_save_and_load(tmp_path: Path):
    db_path = tmp_path / "autonomy2.db"
    store = AutonomyStore(db_path=str(db_path))
    state = AutonomyState(
        traits=[Trait(name="Curiosité intellectuelle", intensity=0.9)],
        gauges=[Gauge(name="exploration", current=0.5, decay_rate=0.1)],
        desires=[Desire(name="Explorer", priority=0.7, generating_trait="Curiosité intellectuelle", generating_gauge="exploration")],
        dreams=[Dream(name="Devenir pleinement autonome", progress=0.2)],
        mood=0.5,
    )
    store.save_state(state)
    loaded = store.load_state()
    assert loaded.traits[0].name == "Curiosité intellectuelle"
    assert loaded.gauges[0].name == "exploration"
    assert loaded.desires[0].name == "Explorer"

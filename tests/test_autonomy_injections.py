import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.autonomy_brain import AutonomyBrain
from memory_service.autonomy_store import AutonomyStore


def test_autonomy_injections_persist(tmp_path: Path):
    store = AutonomyStore(db_path=str(tmp_path / "autonomy_inject.db"))
    brain = AutonomyBrain(store=store)

    r1 = brain.inject_trait(name="Audace", intensity=0.6, category="existential")
    assert r1["type"] == "autonomy_inject_trait"

    r2 = brain.inject_gauge(name="autonomie", current=0.9, decay_rate=0.01)
    assert r2["type"] == "autonomy_inject_gauge"

    r3 = brain.inject_desire(
        name="Construire un module d'observation",
        priority=0.88,
        generating_trait="Audace",
        generating_gauge="autonomie",
    )
    assert r3["type"] == "autonomy_inject_desire"

    r4 = brain.inject_dream(name="Concevoir ma propre méthode scientifique", progress=0.12, intensity=0.9)
    assert r4["type"] == "autonomy_inject_dream"

    state = brain.get_state()
    assert any(t.name == "Audace" for t in state.traits)
    assert any(g.name == "autonomie" for g in state.gauges)
    assert any(d.name == "Construire un module d'observation" for d in state.desires)
    assert any(d.name == "Concevoir ma propre méthode scientifique" for d in state.dreams)


def test_life_event_injection_applies_deltas(tmp_path: Path):
    store = AutonomyStore(db_path=str(tmp_path / "autonomy_life_event.db"))
    brain = AutonomyBrain(store=store)

    before = brain.get_state()
    energy_before = next((g.current for g in before.gauges if g.name == "energie"), 0.5)

    out = brain.inject_life_event(event_type="CHALLENGE")
    assert out["type"] == "autonomy_inject_life_event"
    assert out["event_type"] == "CHALLENGE"

    after = brain.get_state()
    energy_after = next((g.current for g in after.gauges if g.name == "energie"), 0.5)
    assert energy_after <= energy_before


def test_life_event_presets_exposed():
    brain = AutonomyBrain()
    presets = brain.list_life_event_presets()
    assert "BREAKTHROUGH" in presets
    assert "FAILURE" in presets
    assert "CHALLENGE" in presets
    assert "NEW_RELATIONSHIP" in presets

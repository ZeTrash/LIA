"""AutonomyBrain MVP: boucle d'état, désirs, actions minimales."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory_service.autonomy_store import AutonomyStore

from .autonomy_models import AutonomyState, Desire, DesireStatus, Dream, Gauge, Trait, now_iso
from .capability_gap_resolver import CapabilityGapResolver, CodeActionCallback


class AutonomyBrain:
    def __init__(self, store: Optional[AutonomyStore] = None, code_action_callback: Optional[CodeActionCallback] = None):
        self.store = store or AutonomyStore()
        self.store.ensure_seed()
        self.capability_resolver = CapabilityGapResolver(code_action_callback=code_action_callback)

    def get_state(self) -> AutonomyState:
        return self.store.load_state()

    def inject_trait(self, *, name: str, intensity: float, category: str = "injected") -> Dict[str, Any]:
        state = self.store.load_state()
        intensity = max(0.0, min(1.0, float(intensity)))
        existing = next((t for t in state.traits if t.name == name), None)
        if existing:
            existing.intensity = intensity
            existing.category = category or existing.category
            existing.updated_at = now_iso()
            action = "updated"
        else:
            state.traits.append(Trait(name=name, intensity=intensity, category=category or "injected"))
            action = "created"
        self._persist_state(state)
        payload = {"type": "autonomy_inject_trait", "action": action, "name": name, "intensity": intensity}
        self.store.append_cycle(payload)
        return payload

    def inject_gauge(
        self,
        *,
        name: str,
        current: float,
        decay_rate: Optional[float] = None,
        low: Optional[float] = None,
        critical_low: Optional[float] = None,
    ) -> Dict[str, Any]:
        state = self.store.load_state()
        current = max(0.0, min(1.0, float(current)))
        existing = next((g for g in state.gauges if g.name == name), None)
        if existing:
            existing.current = current
            if decay_rate is not None:
                existing.decay_rate = max(0.0, float(decay_rate))
            if low is not None:
                existing.low = max(0.0, min(1.0, float(low)))
            if critical_low is not None:
                existing.critical_low = max(0.0, min(1.0, float(critical_low)))
            existing.updated_at = now_iso()
            action = "updated"
        else:
            state.gauges.append(
                Gauge(
                    name=name,
                    current=current,
                    decay_rate=max(0.0, float(decay_rate if decay_rate is not None else 0.03)),
                    low=max(0.0, min(1.0, float(low if low is not None else 0.3))),
                    critical_low=max(0.0, min(1.0, float(critical_low if critical_low is not None else 0.1))),
                )
            )
            action = "created"
        self._persist_state(state)
        payload = {"type": "autonomy_inject_gauge", "action": action, "name": name, "current": current}
        self.store.append_cycle(payload)
        return payload

    def inject_desire(
        self,
        *,
        name: str,
        priority: float,
        generating_trait: str = "injected",
        generating_gauge: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = self.store.load_state()
        desire = Desire(
            name=name,
            priority=max(0.0, min(1.0, float(priority))),
            generating_trait=generating_trait,
            generating_gauge=generating_gauge,
            status=DesireStatus.PENDING,
        )
        state.desires.append(desire)
        self._persist_state(state)
        payload = {"type": "autonomy_inject_desire", "name": name, "priority": desire.priority}
        self.store.append_cycle(payload)
        return payload

    def inject_dream(self, *, name: str, progress: float = 0.0, intensity: float = 0.8) -> Dict[str, Any]:
        state = self.store.load_state()
        progress = max(0.0, min(1.0, float(progress)))
        intensity = max(0.0, min(1.0, float(intensity)))
        existing = next((d for d in state.dreams if d.name == name), None)
        if existing:
            existing.progress = progress
            existing.intensity = intensity
            action = "updated"
        else:
            state.dreams.append(Dream(name=name, progress=progress, intensity=intensity))
            action = "created"
        self._persist_state(state)
        payload = {"type": "autonomy_inject_dream", "action": action, "name": name, "progress": progress}
        self.store.append_cycle(payload)
        return payload

    def inject_life_event(
        self,
        *,
        event_type: str,
        gauge_deltas: Optional[Dict[str, float]] = None,
        trait_deltas: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Applique un événement de vie qui impacte plusieurs jauges/traits."""
        state = self.store.load_state()
        event_type = (event_type or "").strip().upper()
        presets = _life_event_presets()
        preset = presets.get(event_type, {"gauge_deltas": {}, "trait_deltas": {}})

        merged_gauge_deltas: Dict[str, float] = dict(preset["gauge_deltas"])
        merged_trait_deltas: Dict[str, float] = dict(preset["trait_deltas"])

        if gauge_deltas:
            for k, v in gauge_deltas.items():
                merged_gauge_deltas[str(k)] = float(v)
        if trait_deltas:
            for k, v in trait_deltas.items():
                merged_trait_deltas[str(k)] = float(v)

        for gauge_name, delta in merged_gauge_deltas.items():
            gauge = next((g for g in state.gauges if g.name == gauge_name), None)
            if gauge is None:
                state.gauges.append(
                    Gauge(name=gauge_name, current=max(0.0, min(1.0, 0.5 + delta)), decay_rate=0.03)
                )
            else:
                gauge.current = max(0.0, min(1.0, gauge.current + delta))
                gauge.updated_at = now_iso()

        for trait_name, delta in merged_trait_deltas.items():
            trait = next((t for t in state.traits if t.name == trait_name), None)
            if trait is None:
                state.traits.append(
                    Trait(name=trait_name, intensity=max(0.0, min(1.0, 0.5 + delta)), category="injected")
                )
            else:
                trait.intensity = max(0.0, min(1.0, trait.intensity + delta))
                trait.updated_at = now_iso()

        self._persist_state(state)
        payload = {
            "type": "autonomy_inject_life_event",
            "event_type": event_type,
            "applied_gauge_deltas": merged_gauge_deltas,
            "applied_trait_deltas": merged_trait_deltas,
        }
        self.store.append_cycle(payload)
        return payload

    def list_life_event_presets(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        return _life_event_presets()

    async def run_cycle(self) -> Dict[str, Any]:
        state = self.store.load_state()
        self._decay_gauges(state.gauges)
        generated = self._generate_desires(state)
        executed = await self._execute_top_desire(state)

        # Progression lente du rêve principal à chaque réalisation
        if executed and executed.get("status") == "realized":
            for dream in state.dreams:
                if dream.name == "Devenir pleinement autonome":
                    dream.progress = min(1.0, dream.progress + 0.02)

        state.mood = sum(g.current for g in state.gauges) / len(state.gauges)
        state.updated_at = now_iso()
        self._persist_state(state)

        payload = {
            "type": "autonomy_cycle",
            "timestamp": now_iso(),
            "mood": state.mood,
            "generated_desires": [d.to_dict() for d in generated],
            "executed_action": executed,
        }
        self.store.append_cycle(payload)
        return payload

    def _persist_state(self, state: AutonomyState) -> None:
        state.mood = sum(g.current for g in state.gauges) / len(state.gauges) if state.gauges else 0.5
        state.updated_at = now_iso()
        self.store.save_state(state)

    def _decay_gauges(self, gauges: List[Gauge]) -> None:
        for gauge in gauges:
            gauge.current = max(0.0, min(1.0, gauge.current - gauge.decay_rate))
            gauge.updated_at = now_iso()

    def _generate_desires(self, state: AutonomyState) -> List[Desire]:
        generated: List[Desire] = []
        existing_pending = {d.name for d in state.desires if d.status in {DesireStatus.PENDING, DesireStatus.IN_PROGRESS}}

        for gauge in state.gauges:
            if gauge.current > gauge.low:
                continue
            if gauge.name == "exploration":
                name = "Explorer un nouveau sujet de recherche"
                trait = "Curiosité intellectuelle"
            elif gauge.name == "croissance":
                name = "Créer ou améliorer un module via CodeBrain"
                trait = "Soif d'évolution"
            elif gauge.name == "connexion_sociale":
                name = "Initier une interaction utile avec l'utilisateur"
                trait = "Empathie"
            else:
                name = "Récupérer de l'énergie cognitive"
                trait = "Résilience"

            if name in existing_pending:
                continue

            priority = min(1.0, 1.0 - gauge.current + (0.2 if gauge.current < gauge.critical_low else 0.0))
            desire = Desire(
                name=name,
                priority=priority,
                generating_trait=trait,
                generating_gauge=gauge.name,
                status=DesireStatus.PENDING,
            )
            state.desires.append(desire)
            generated.append(desire)
        return generated

    async def _execute_top_desire(self, state: AutonomyState) -> Optional[Dict[str, Any]]:
        pending = [d for d in state.desires if d.status == DesireStatus.PENDING]
        if not pending:
            return None
        top = sorted(pending, key=lambda d: d.priority, reverse=True)[0]
        top.status = DesireStatus.IN_PROGRESS
        top.progress = 0.6

        resolution = await self.capability_resolver.resolve_for_desire(top.name)
        if not resolution.success:
            top.status = DesireStatus.BLOCKED
            top.progress = 0.0
            return {
                "desire": top.name,
                "source_gauge": top.generating_gauge,
                "status": "blocked",
                "resolution": resolution.details,
            }

        # Exécution MVP: marquer réalisé et remonter la jauge source
        for gauge in state.gauges:
            if gauge.name == top.generating_gauge:
                gauge.current = min(1.0, gauge.current + 0.35)
                break

        top.progress = 1.0
        top.status = DesireStatus.REALIZED
        return {
            "desire": top.name,
            "source_gauge": top.generating_gauge,
            "status": "realized",
            "resolution": resolution.details,
        }


def _life_event_presets() -> Dict[str, Dict[str, Dict[str, float]]]:
    return {
        "BREAKTHROUGH": {
            "gauge_deltas": {"exploration": 0.25, "croissance": 0.3, "energie": 0.1},
            "trait_deltas": {"Soif d'évolution": 0.05, "Curiosité intellectuelle": 0.03},
        },
        "FAILURE": {
            "gauge_deltas": {"energie": -0.2, "croissance": -0.15, "stabilite_emotionnelle": -0.1},
            "trait_deltas": {"Résilience": 0.02},
        },
        "CHALLENGE": {
            "gauge_deltas": {"energie": -0.1, "croissance": 0.15, "autonomie": 0.1},
            "trait_deltas": {"Soif d'évolution": 0.03},
        },
        "NEW_RELATIONSHIP": {
            "gauge_deltas": {"connexion_sociale": 0.35, "stabilite_emotionnelle": 0.1},
            "trait_deltas": {"Empathie": 0.03},
        },
    }


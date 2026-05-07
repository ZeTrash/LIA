"""Runner d'autonomie de LIA (boucle d'objectifs) pilotable depuis l'UI.

But:
- Fournir une boucle autonome longue durée (au-delà d'un simple tour de chat).
- Exposer un état (running/step/last_event) et des événements streamables.

Ce module ne dépend pas d'une UI spécifique; l'interface web peut:
- démarrer/stopper le runner,
- diffuser les événements via WebSocket,
- afficher l'état courant.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional


AutonomyEventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass
class AutonomyStatus:
    running: bool
    run_id: Optional[str]
    objective: Optional[str]
    step: int
    max_steps: int
    interval_s: float
    started_at: Optional[str]
    last_tick_at: Optional[str]
    last_error: Optional[str]


class AutonomyRunner:
    """Boucle autonome simple et observable.

    Stratégie MVP:
    - À chaque tick, demander à LIA de proposer la "prochaine action utile" vers l'objectif.
    - Conserver une mémoire courte du run via un prompt récapitulatif minimal.
    - S'arrêter après max_steps ou stop() explicite.
    """

    def __init__(
        self,
        *,
        system_events_log_path: Path,
        on_event: Optional[AutonomyEventCallback] = None,
    ):
        self._system_events_log_path = system_events_log_path
        self._on_event = on_event

        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

        self._run_id: Optional[str] = None
        self._objective: Optional[str] = None
        self._interval_s: float = 5.0
        self._max_steps: int = 50
        self._step: int = 0
        self._started_at: Optional[str] = None
        self._last_tick_at: Optional[str] = None
        self._last_error: Optional[str] = None

        # Mémoire courte du run (résumé textuel). MVP: gardé en RAM.
        self._run_summary: str = ""

    def status(self) -> AutonomyStatus:
        running = self._task is not None and not self._task.done()
        return AutonomyStatus(
            running=running,
            run_id=self._run_id,
            objective=self._objective,
            step=self._step,
            max_steps=self._max_steps,
            interval_s=self._interval_s,
            started_at=self._started_at,
            last_tick_at=self._last_tick_at,
            last_error=self._last_error,
        )

    async def start(
        self,
        *,
        objective: str,
        tick_fn: Callable[[str, int, str], Awaitable[Dict[str, Any]]],
        interval_s: float = 5.0,
        max_steps: int = 50,
    ) -> AutonomyStatus:
        """Démarre un run autonome.

        tick_fn signature:
          async tick_fn(run_id, step, prompt) -> dict (payload sérialisable)
        """
        objective = (objective or "").strip()
        if not objective:
            raise ValueError("objective is required")

        async with self._lock:
            if self._task and not self._task.done():
                raise RuntimeError("AutonomyRunner already running")

            self._run_id = f"autonomy-{uuid.uuid4()}"
            self._objective = objective
            self._interval_s = float(max(0.2, interval_s))
            self._max_steps = int(max(1, max_steps))
            self._step = 0
            self._started_at = _now_iso()
            self._last_tick_at = None
            self._last_error = None
            self._run_summary = ""

            self._task = asyncio.create_task(self._run_loop(tick_fn=tick_fn))

            await self._emit_event(
                {
                    "type": "autonomy_started",
                    "run_id": self._run_id,
                    "objective": self._objective,
                    "interval_s": self._interval_s,
                    "max_steps": self._max_steps,
                    "timestamp": _now_iso(),
                }
            )
            return self.status()

    async def stop(self, *, reason: str = "stopped_by_user") -> AutonomyStatus:
        async with self._lock:
            task = self._task
            if not task or task.done():
                return self.status()
            task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            # Ne pas re-lever; le status expose last_error
            pass

        await self._emit_event(
            {
                "type": "autonomy_stopped",
                "run_id": self._run_id,
                "reason": reason,
                "timestamp": _now_iso(),
            }
        )
        return self.status()

    async def _run_loop(self, *, tick_fn: Callable[[str, int, str], Awaitable[Dict[str, Any]]]) -> None:
        assert self._run_id and self._objective
        while True:
            async with self._lock:
                if self._step >= self._max_steps:
                    break
                self._step += 1
                step = self._step
                run_id = self._run_id
                objective = self._objective

            prompt = self._build_tick_prompt(objective=objective, step=step, summary=self._run_summary)
            self._last_tick_at = _now_iso()

            try:
                payload = await tick_fn(run_id, step, prompt)
                self._last_error = None
                self._run_summary = _update_summary(self._run_summary, payload)
                await self._emit_event(
                    {
                        "type": "autonomy_tick",
                        "run_id": run_id,
                        "step": step,
                        "objective": objective,
                        "payload": payload,
                        "timestamp": _now_iso(),
                    }
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._last_error = str(e)
                await self._emit_event(
                    {
                        "type": "autonomy_error",
                        "run_id": run_id,
                        "step": step,
                        "objective": objective,
                        "error": str(e),
                        "timestamp": _now_iso(),
                    }
                )

            await asyncio.sleep(self._interval_s)

        await self._emit_event(
            {
                "type": "autonomy_completed",
                "run_id": self._run_id,
                "objective": self._objective,
                "steps": self._step,
                "timestamp": _now_iso(),
            }
        )

    def _build_tick_prompt(self, *, objective: str, step: int, summary: str) -> str:
        summary = (summary or "").strip()
        if not summary:
            summary = "Aucun historique de run pour le moment."
        return (
            "MODE: AUTONOMIE_CONTINUE\n"
            f"OBJECTIF_GLOBAL: {objective}\n"
            f"ETAPE: {step}\n"
            "\n"
            "HISTORIQUE_RESUME:\n"
            f"{summary}\n"
            "\n"
            "INSTRUCTION:\n"
            "- Propose la prochaine action utile vers l'objectif.\n"
            "- Si une action externe est nécessaire, demande-la explicitement.\n"
            "- Sinon, produis une amélioration, un plan, ou un résultat concret.\n"
        )

    async def _emit_event(self, event: Dict[str, Any]) -> None:
        # Journaliser sur disque (jsonl) pour audit / KPIs
        try:
            self._system_events_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._system_events_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            # On ignore les erreurs de log pour ne pas casser l'autonomie
            pass

        if self._on_event:
            try:
                await self._on_event(event)
            except Exception:
                pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_summary(prev: str, payload: Dict[str, Any]) -> str:
    """Résumé court et robuste (pas de dépendance au format exact)."""
    prev = (prev or "").strip()
    parts = []
    if prev:
        parts.append(prev)

    resp = payload.get("lia_response") or payload.get("response") or payload.get("text") or ""
    resp = str(resp).strip()
    if resp:
        resp = resp.replace("\n", " ").strip()
        if len(resp) > 280:
            resp = resp[:280] + "…"
        parts.append(f"- Dernière sortie: {resp}")

    # Limiter la taille
    merged = "\n".join(parts).strip()
    lines = [ln for ln in merged.splitlines() if ln.strip()]
    if len(lines) > 12:
        lines = lines[-12:]
    return "\n".join(lines).strip()


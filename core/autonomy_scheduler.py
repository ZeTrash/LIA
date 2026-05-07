"""Scheduler autonome pour exécuter AutonomyBrain en arrière-plan."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from .autonomy_brain import AutonomyBrain
from .autonomy_models import now_iso


EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass
class SchedulerStatus:
    running: bool
    interval_seconds: float
    cycles_completed: int
    started_at: Optional[str]
    last_cycle_at: Optional[str]
    last_error: Optional[str]


class AutonomyScheduler:
    def __init__(self, brain: Optional[AutonomyBrain] = None, on_event: Optional[EventCallback] = None):
        self.brain = brain or AutonomyBrain()
        self.on_event = on_event
        self.interval_seconds: float = 60.0
        self.cycles_completed: int = 0
        self.started_at: Optional[str] = None
        self.last_cycle_at: Optional[str] = None
        self.last_error: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    def status(self) -> SchedulerStatus:
        return SchedulerStatus(
            running=self._task is not None and not self._task.done(),
            interval_seconds=self.interval_seconds,
            cycles_completed=self.cycles_completed,
            started_at=self.started_at,
            last_cycle_at=self.last_cycle_at,
            last_error=self.last_error,
        )

    async def start(self, interval_seconds: float = 60.0) -> SchedulerStatus:
        if self._task and not self._task.done():
            return self.status()
        self.interval_seconds = max(0.2, float(interval_seconds))
        self.cycles_completed = 0
        self.started_at = now_iso()
        self.last_cycle_at = None
        self.last_error = None
        self._task = asyncio.create_task(self._loop())
        await self._emit({"type": "autonomy_scheduler_started", "timestamp": now_iso(), "interval_seconds": self.interval_seconds})
        return self.status()

    async def stop(self) -> SchedulerStatus:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._emit({"type": "autonomy_scheduler_stopped", "timestamp": now_iso()})
        return self.status()

    async def run_single_cycle(self) -> Dict[str, Any]:
        payload = await self.brain.run_cycle()
        self.cycles_completed += 1
        self.last_cycle_at = now_iso()
        await self._emit(payload)
        return payload

    async def _loop(self) -> None:
        while True:
            try:
                await self.run_single_cycle()
                self.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.last_error = str(e)
                await self._emit({"type": "autonomy_scheduler_error", "timestamp": now_iso(), "error": str(e)})
            await asyncio.sleep(self.interval_seconds)

    async def _emit(self, event: Dict[str, Any]) -> None:
        if self.on_event:
            await self.on_event(event)


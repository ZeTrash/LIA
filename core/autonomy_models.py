"""Modèles minimaux pour le système d'autonomie."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DesireStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REALIZED = "realized"
    BLOCKED = "blocked"


@dataclass
class Trait:
    name: str
    intensity: float
    category: str = "cognitive"
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Gauge:
    name: str
    current: float
    decay_rate: float
    low: float = 0.3
    critical_low: float = 0.1
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Desire:
    name: str
    priority: float
    generating_trait: str
    generating_gauge: Optional[str]
    status: DesireStatus = DesireStatus.PENDING
    progress: float = 0.0
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass
class Dream:
    name: str
    progress: float = 0.0
    intensity: float = 0.7
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomyState:
    traits: List[Trait]
    gauges: List[Gauge]
    desires: List[Desire]
    dreams: List[Dream]
    mood: float
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traits": [t.to_dict() for t in self.traits],
            "gauges": [g.to_dict() for g in self.gauges],
            "desires": [d.to_dict() for d in self.desires],
            "dreams": [d.to_dict() for d in self.dreams],
            "mood": self.mood,
            "updated_at": self.updated_at,
        }


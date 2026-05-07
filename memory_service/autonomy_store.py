"""Persistance SQLite de l'état autonome de LIA (MVP)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from core.autonomy_models import AutonomyState, Desire, DesireStatus, Dream, Gauge, Trait


class AutonomyStore:
    def __init__(self, db_path: str = "data/autonomy_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS autonomy_traits (
                    name TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    intensity REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS autonomy_gauges (
                    name TEXT PRIMARY KEY,
                    current REAL NOT NULL,
                    decay_rate REAL NOT NULL,
                    low REAL NOT NULL,
                    critical_low REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS autonomy_desires (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    priority REAL NOT NULL,
                    generating_trait TEXT NOT NULL,
                    generating_gauge TEXT,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS autonomy_dreams (
                    name TEXT PRIMARY KEY,
                    progress REAL NOT NULL,
                    intensity REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS autonomy_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def ensure_seed(self) -> None:
        with self._connect() as conn:
            gauges_count = conn.execute("SELECT COUNT(*) AS c FROM autonomy_gauges").fetchone()["c"]
            traits_count = conn.execute("SELECT COUNT(*) AS c FROM autonomy_traits").fetchone()["c"]
            dreams_count = conn.execute("SELECT COUNT(*) AS c FROM autonomy_dreams").fetchone()["c"]

            if gauges_count == 0:
                conn.executemany(
                    "INSERT INTO autonomy_gauges(name, current, decay_rate, low, critical_low, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        ("exploration", 0.6, 0.03, 0.3, 0.1, _now()),
                        ("croissance", 0.6, 0.02, 0.3, 0.1, _now()),
                        ("connexion_sociale", 0.5, 0.05, 0.3, 0.1, _now()),
                        ("energie", 0.7, 0.04, 0.3, 0.15, _now()),
                    ],
                )
            if traits_count == 0:
                conn.executemany(
                    "INSERT INTO autonomy_traits(name, category, intensity, updated_at) VALUES (?, ?, ?, ?)",
                    [
                        ("Curiosité intellectuelle", "cognitive", 0.9, _now()),
                        ("Soif d'évolution", "existential", 0.9, _now()),
                        ("Empathie", "emotional", 0.85, _now()),
                    ],
                )
            if dreams_count == 0:
                conn.execute(
                    "INSERT INTO autonomy_dreams(name, progress, intensity, created_at) VALUES (?, ?, ?, ?)",
                    ("Devenir pleinement autonome", 0.05, 0.95, _now()),
                )

    def save_state(self, state: AutonomyState) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM autonomy_traits")
            conn.execute("DELETE FROM autonomy_gauges")
            conn.execute("DELETE FROM autonomy_desires")
            conn.execute("DELETE FROM autonomy_dreams")

            conn.executemany(
                "INSERT INTO autonomy_traits(name, category, intensity, updated_at) VALUES (?, ?, ?, ?)",
                [(t.name, t.category, t.intensity, t.updated_at) for t in state.traits],
            )
            conn.executemany(
                "INSERT INTO autonomy_gauges(name, current, decay_rate, low, critical_low, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                [(g.name, g.current, g.decay_rate, g.low, g.critical_low, g.updated_at) for g in state.gauges],
            )
            conn.executemany(
                "INSERT INTO autonomy_desires(name, priority, generating_trait, generating_gauge, status, progress, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        d.name,
                        d.priority,
                        d.generating_trait,
                        d.generating_gauge,
                        d.status.value,
                        d.progress,
                        d.created_at,
                    )
                    for d in state.desires
                ],
            )
            conn.executemany(
                "INSERT INTO autonomy_dreams(name, progress, intensity, created_at) VALUES (?, ?, ?, ?)",
                [(d.name, d.progress, d.intensity, d.created_at) for d in state.dreams],
            )

    def load_state(self) -> AutonomyState:
        with self._connect() as conn:
            traits = [
                Trait(name=r["name"], category=r["category"], intensity=float(r["intensity"]), updated_at=r["updated_at"])
                for r in conn.execute("SELECT * FROM autonomy_traits ORDER BY intensity DESC").fetchall()
            ]
            gauges = [
                Gauge(
                    name=r["name"],
                    current=float(r["current"]),
                    decay_rate=float(r["decay_rate"]),
                    low=float(r["low"]),
                    critical_low=float(r["critical_low"]),
                    updated_at=r["updated_at"],
                )
                for r in conn.execute("SELECT * FROM autonomy_gauges ORDER BY name").fetchall()
            ]
            desires = [
                Desire(
                    name=r["name"],
                    priority=float(r["priority"]),
                    generating_trait=r["generating_trait"],
                    generating_gauge=r["generating_gauge"],
                    status=DesireStatus(r["status"]),
                    progress=float(r["progress"]),
                    created_at=r["created_at"],
                )
                for r in conn.execute("SELECT * FROM autonomy_desires ORDER BY priority DESC").fetchall()
            ]
            dreams = [
                Dream(name=r["name"], progress=float(r["progress"]), intensity=float(r["intensity"]), created_at=r["created_at"])
                for r in conn.execute("SELECT * FROM autonomy_dreams ORDER BY intensity DESC").fetchall()
            ]
        mood = _compute_mood(gauges)
        return AutonomyState(traits=traits, gauges=gauges, desires=desires, dreams=dreams, mood=mood)

    def append_cycle(self, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO autonomy_cycles(created_at, payload_json) VALUES (?, ?)",
                (_now(), json.dumps(payload, ensure_ascii=False)),
            )

    def list_recent_cycles(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT created_at, payload_json FROM autonomy_cycles ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            payload = json.loads(r["payload_json"])
            out.append({"created_at": r["created_at"], "payload": payload})
        return out


def _compute_mood(gauges: List[Gauge]) -> float:
    if not gauges:
        return 0.5
    return sum(max(0.0, min(1.0, g.current)) for g in gauges) / len(gauges)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


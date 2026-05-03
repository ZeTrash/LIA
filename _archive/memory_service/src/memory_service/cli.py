"""CLI utilitaire pour seed et supervision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import create_session_factory
from .models import (
    InteractionModel,
    SessionGoalModel,
    SouvenirModel,
    TraitModel,
    TraitVersionModel,
)
from .store import MemoryStore

DEFAULT_SEED = {
    "traits": [
        {
            "trait_id": "stakeholders",
            "type": "knowledge",
            "label": "Contacts clés",
            "value": "Alice (Produit), Karim (Ops)",
            "weight": 0.75,
            "confidence": 0.68,
        }
    ],
    "session_goals": [
        {
            "goal_id": "g-onboarding",
            "session_id": "default",
            "priority": 0.85,
            "description": "Onboarder rapidement les nouveaux collaborateurs",
            "blocking_conditions": ["docs_incomplètes"],
        }
    ],
    "souvenirs": [
        {
            "category": "fact",
            "content": "Le client Orion valorise les réponses synthétiques (<120 mots).",
            "tags": ["client_orion", "style"],
            "importance_score": 0.78,
            "recency_score": 0.8,
            "emotion_score": 0.1,
            "ttl": 120,
            "source": "seed",
        },
        {
            "category": "alert",
            "content": "Incident janvier : confusion entre Alice (Produit) et Alicia (Finance).",
            "tags": ["incident", "naming"],
            "importance_score": 0.82,
            "recency_score": 0.7,
            "emotion_score": 0.3,
            "ttl": 60,
            "source": "seed",
        },
    ],
    "interactions": [
        {
            "session_id": "default",
            "prompt": "Peux-tu résumer la réunion produit ?",
            "response": "Réunion centrée sur la roadmap Q1, besoin d'insister sur la stabilité mobile.",
            "derived_traits": ["tone"],
            "scores": {"usefulness": 0.86, "coherence": 0.92, "tone": 0.88, "emotion": "positive"},
        }
    ],
}


def seed_database(seed_path: Optional[str] = None, seed_payload: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """Alimente la base avec un jeu de données."""

    settings = get_settings()
    session_factory = create_session_factory(settings)
    payload = seed_payload or load_seed_payload(seed_path, settings.data_dir)
    summary = {"traits": 0, "session_goals": 0, "souvenirs": 0, "interactions": 0}

    with session_factory() as session:
        summary["traits"] = _seed_traits(session, payload.get("traits", []))
        summary["session_goals"] = _seed_goals(session, payload.get("session_goals", []))
        summary["souvenirs"] = _seed_souvenirs(session, payload.get("souvenirs", []))
        summary["interactions"] = _seed_interactions(session, payload.get("interactions", []))
        session.commit()

    return summary


def collect_stats(session_id: str = "default") -> Dict[str, Any]:
    """Renvoie des compteurs simples pour supervision CLI."""

    settings = get_settings()
    session_factory = create_session_factory(settings)
    with session_factory() as session:
        counts = {
            "traits": _count(session, TraitModel),
            "souvenirs": _count(session, SouvenirModel),
            "interactions": _count(session, InteractionModel),
            "session_goals": _count(session, SessionGoalModel),
        }
        goals = session.scalars(select(SessionGoalModel).where(SessionGoalModel.session_id == session_id)).all()
        if not goals:
            goals = session.scalars(select(SessionGoalModel).where(SessionGoalModel.session_id == "default")).all()
        goal_descriptions = [f"{goal.goal_id}: {goal.description}" for goal in goals]
    return {"counts": counts, "goals": goal_descriptions}


def print_metrics() -> None:
    """Affiche les KPI calculés par le store."""

    settings = get_settings()
    session_factory = create_session_factory(settings)
    store = MemoryStore(settings, session_factory)
    metrics = store.get_metrics()
    print("=== KPI Mémoire ===")
    for field, value in metrics.kpis.model_dump().items():
        print(f"- {field}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI mémoire persistante")
    subparsers = parser.add_subparsers(dest="command")

    seed_parser = subparsers.add_parser("seed", help="Insère les données d'exemple")
    seed_parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Chemin vers un fichier JSON de seed (défaut: data/seed_memories.json ou dataset embarqué)",
    )

    stats_parser = subparsers.add_parser("stats", help="Affiche les compteurs principaux")
    stats_parser.add_argument("--session-id", type=str, default="default", help="Session pour lister les objectifs")

    subparsers.add_parser("metrics", help="Affiche les KPI agrégés")

    args = parser.parse_args()
    if args.command == "seed":
        summary = seed_database(args.file)
        print("Seed effectué :", summary)
    elif args.command == "stats":
        report = collect_stats(args.session_id)
        print("=== Compteurs ===")
        for name, value in report["counts"].items():
            print(f"- {name}: {value}")
        print("=== Objectifs actifs ===")
        for goal in report["goals"]:
            print(f"- {goal}")
    elif args.command == "metrics":
        print_metrics()
    else:
        parser.print_help()
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_seed_payload(seed_path: Optional[str], data_dir: str) -> Dict[str, Any]:
    if seed_path:
        path = Path(seed_path)
    else:
        path = Path(data_dir) / "seed_memories.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_SEED


def _seed_traits(session: Session, items: Iterable[Dict[str, Any]]) -> int:
    from datetime import datetime
    import hashlib
    inserted = 0
    for data in items:
        trait_id = data["trait_id"]
        if session.get(TraitModel, trait_id):
            continue
        model = TraitModel(
            trait_id=trait_id,
            type=data.get("type", "custom"),
            label=data.get("label", trait_id),
            value=data.get("value", ""),
            weight=data.get("weight", 0.8),
            confidence=data.get("confidence", 0.7),
            status=data.get("status", "active"),
        )
        model.checksum = hashlib.sha3_256(model.value.encode("utf-8")).hexdigest()
        session.add(model)
        session.flush()
        session.add(
            TraitVersionModel(
                trait_id=model.trait_id,
                version=model.version,
                delta={"value": model.value, "weight": model.weight, "confidence": model.confidence},
                changed_at=datetime.utcnow(),
                changed_by="seed",
            )
        )
        inserted += 1
    return inserted


def _seed_goals(session: Session, items: Iterable[Dict[str, Any]]) -> int:
    from datetime import datetime, timedelta
    inserted = 0
    for data in items:
        if session.get(SessionGoalModel, data["goal_id"]):
            continue
        expires_at = data.get("expires_at")
        if expires_at and isinstance(expires_at, str):
            from dateutil.parser import parse
            expires_at = parse(expires_at)
        elif not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=30)
        session.add(
            SessionGoalModel(
                goal_id=data["goal_id"],
                session_id=data.get("session_id", "default"),
                priority=data.get("priority", 0.5),
                description=data.get("description", ""),
                blocking_conditions=data.get("blocking_conditions", []),
                expires_at=expires_at,
                status=data.get("status", "active"),
            )
        )
        inserted += 1
    return inserted


def _seed_souvenirs(session: Session, items: Iterable[Dict[str, Any]]) -> int:
    from datetime import datetime, timedelta
    import hashlib
    inserted = 0
    for data in items:
        memory_id = data.get("memory_id") or f"seed-{uuid4().hex}"
        if session.get(SouvenirModel, memory_id):
            continue
        content = data.get("content", "")
        content_hash = hashlib.sha3_256(content.encode("utf-8")).hexdigest()
        tags_list = data.get("tags", [])
        tags_text = ",".join(tags_list) if tags_list else None
        ttl_days = data.get("ttl", 45)
        ttl_datetime = datetime.utcnow() + timedelta(days=ttl_days)
        session.add(
            SouvenirModel(
                memory_id=memory_id,
                category=data.get("category", "fact"),
                content=content,
                tags=tags_text,
                importance_score=data.get("importance_score", 0.6),
                recency_score=data.get("recency_score", 0.6),
                emotion_score=data.get("emotion_score", 0.0),
                frequency=data.get("frequency", 1),
                ttl=ttl_datetime,
                source=data.get("source", "seed"),
                hash=content_hash,
            )
        )
        inserted += 1
    return inserted


def _seed_interactions(session: Session, items: Iterable[Dict[str, Any]]) -> int:
    from datetime import datetime
    inserted = 0
    for data in items:
        interaction_id = data.get("interaction_id") or f"seed-{uuid4().hex}"
        if session.get(InteractionModel, interaction_id):
            continue
        prompt = data.get("prompt", "")
        response = data.get("response", "")
        raw_size = len(prompt.encode("utf-8")) + len(response.encode("utf-8"))
        severity = "error" if any("error" in str(a).lower() for a in data.get("anomalies", [])) else "warning" if data.get("anomalies") else "info"
        session.add(
            InteractionModel(
                interaction_id=interaction_id,
                session_id=data.get("session_id", "default"),
                occurred_at=datetime.utcnow(),
                prompt=prompt,
                response=response,
                scores=data.get(
                    "scores",
                    {"usefulness": 0.8, "coherence": 0.9, "tone": 0.9},
                ),
                derived_traits=data.get("derived_traits", []),
                anomalies=data.get("anomalies", []),
                severity=severity,
                raw_size_bytes=raw_size,
            )
        )
        inserted += 1
    return inserted


def _count(session: Session, model: Any) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


if __name__ == "__main__":
    main()

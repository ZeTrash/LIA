"""Analyseur des logs système LIA (JSONL) pour suivi qualité."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Optional


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def analyze_log_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total_events = len(events)
    by_type = Counter(e.get("event", "unknown") for e in events)
    sessions = Counter(e.get("session_id", "none") for e in events)

    # Reconstruction légère des échanges par session
    starts: Dict[str, datetime] = {}
    latencies: List[float] = []
    errors = 0
    brain_counter = Counter()
    brain_model_counter = Counter()
    response_lengths: List[int] = []
    process_chunk_counts: List[int] = []

    for e in events:
        et = e.get("event")
        sid = str(e.get("session_id") or "none")
        payload = e.get("payload") or {}
        ts = _parse_ts(e.get("ts"))

        if et == "exchange_start" and ts:
            starts[sid] = ts
        elif et == "exchange_end":
            if ts and sid in starts:
                latencies.append((ts - starts[sid]).total_seconds())
            response = str(payload.get("response") or "")
            response_lengths.append(len(response))
            process_chunk_counts.append(len(payload.get("process_chunks") or []))
        elif et == "exchange_error":
            errors += 1
        elif et == "router_decision":
            brain = payload.get("brain")
            brain_model = payload.get("brain_from_model")
            if brain:
                brain_counter[str(brain)] += 1
            if brain_model:
                brain_model_counter[str(brain_model)] += 1

    return {
        "path": str(path),
        "total_events": total_events,
        "events_by_type": dict(by_type),
        "total_sessions": len(sessions),
        "top_sessions": sessions.most_common(10),
        "errors": errors,
        "error_rate": (errors / max(total_events, 1)),
        "latency": {
            "count": len(latencies),
            "avg_s": mean(latencies) if latencies else 0.0,
            "median_s": median(latencies) if latencies else 0.0,
            "p95_s": sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0.0,
        },
        "brains": dict(brain_counter),
        "brains_from_model": dict(brain_model_counter),
        "response_length": {
            "count": len(response_lengths),
            "avg_chars": mean(response_lengths) if response_lengths else 0.0,
            "median_chars": median(response_lengths) if response_lengths else 0.0,
        },
        "process_chunks": {
            "count": len(process_chunk_counts),
            "avg_chunks": mean(process_chunk_counts) if process_chunk_counts else 0.0,
            "median_chunks": median(process_chunk_counts) if process_chunk_counts else 0.0,
        },
    }


def print_report(report: Dict[str, Any]) -> None:
    print("=" * 72)
    print("LIA System Logs Report")
    print("=" * 72)
    print(f"File:           {report['path']}")
    print(f"Total events:   {report['total_events']}")
    print(f"Total sessions: {report['total_sessions']}")
    print(f"Errors:         {report['errors']} ({report['error_rate']*100:.2f}%)")
    print("-" * 72)

    print("Events by type:")
    for k, v in sorted(report["events_by_type"].items(), key=lambda kv: kv[1], reverse=True):
        print(f"  - {k}: {v}")
    print("-" * 72)

    print("Latency (exchange_end - exchange_start):")
    lat = report["latency"]
    print(f"  - count:  {lat['count']}")
    print(f"  - avg:    {lat['avg_s']:.2f}s")
    print(f"  - median: {lat['median_s']:.2f}s")
    print(f"  - p95:    {lat['p95_s']:.2f}s")
    print("-" * 72)

    print("Brain routing distribution:")
    brains = report["brains"]
    if brains:
        for k, v in sorted(brains.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  - {k}: {v}")
    else:
        print("  - (no router_decision events)")

    print("Brain routing (from router model):")
    brains_m = report["brains_from_model"]
    if brains_m:
        for k, v in sorted(brains_m.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  - {k}: {v}")
    else:
        print("  - (no brain_from_model values)")
    print("-" * 72)

    rl = report["response_length"]
    print("Response lengths:")
    print(f"  - count:  {rl['count']}")
    print(f"  - avg:    {rl['avg_chars']:.1f} chars")
    print(f"  - median: {rl['median_chars']:.1f} chars")

    pc = report["process_chunks"]
    print("Process chunk density:")
    print(f"  - count:  {pc['count']}")
    print(f"  - avg:    {pc['avg_chunks']:.2f}")
    print(f"  - median: {pc['median_chunks']:.2f}")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse les logs système LIA (JSONL).")
    parser.add_argument(
        "--log-file",
        default="logs/lia_system_events.jsonl",
        help="Chemin du fichier JSONL de logs système",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Chemin optionnel pour exporter le rapport JSON",
    )
    args = parser.parse_args()

    report = analyze_log_file(Path(args.log_file))
    print_report(report)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON report saved to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


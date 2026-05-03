"""Serveur mock basé sur l'OpenAPI LIA mémoire locale."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

import uvicorn
import yaml
from fastapi import Body, FastAPI, HTTPException, Query

BASE_DIR = Path(__file__).resolve().parents[2]
SPEC_PATH = BASE_DIR / "charge_timeline" / "etape1_cahier_charges" / "livrables" / "api_spec_openapi.yaml"
SAMPLES_PATH = Path(__file__).with_name("sample_payloads.json")

with SPEC_PATH.open("r", encoding="utf-8") as spec_file:
    OPENAPI_SPEC: Dict[str, Any] = yaml.safe_load(spec_file)

with SAMPLES_PATH.open("r", encoding="utf-8") as samples_file:
    SAMPLE_PAYLOADS: Dict[str, Any] = json.load(samples_file)

app = FastAPI(
    title="LIA Memory API Mock",
    version=OPENAPI_SPEC["info"]["version"],
    description="Mock server générant des réponses de démonstration conformes à l'OpenAPI.",
    docs_url="/docs",
    redoc_url="/redoc",
)


def custom_openapi() -> Dict[str, Any]:
    return OPENAPI_SPEC


app.openapi = custom_openapi  # type: ignore[assignment]


@app.get("/context")
async def get_context(session_id: str = Query(...), max_memories: int = Query(12, ge=1, le=40)) -> Dict[str, Any]:
    payload = copy.deepcopy(SAMPLE_PAYLOADS["context"])
    payload["session_goals"] = [
        {**goal, "session_id": session_id}
        for goal in payload.get("session_goals", [])
    ]
    payload["memories"] = payload.get("memories", [])[:max_memories]
    payload.setdefault("governance_metadata", {})["context_version"] = OPENAPI_SPEC["info"]["version"]
    payload.setdefault("governance_metadata", {})["build_time_ms"] = 150
    payload["trace_id"] = "mock-trace-id"
    payload["cache_hit"] = False
    payload["context_checksum"] = "mock-checksum"
    return payload


@app.post("/interaction", status_code=201)
async def post_interaction(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    response = copy.deepcopy(SAMPLE_PAYLOADS["interaction"])
    response["session_id"] = payload.get("session_id", response.get("session_id"))
    response["prompt"] = payload.get("prompt", response.get("prompt"))
    response["response"] = payload.get("response", response.get("response"))
    response.setdefault("interaction_id", payload.get("interaction_id", "mock-interaction"))
    return response


@app.post("/trait-update")
async def post_trait_update(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    trait_id = payload.get("trait_id")
    if not trait_id:
        raise HTTPException(status_code=422, detail="trait_id manquant")
    response = copy.deepcopy(SAMPLE_PAYLOADS["trait_update"])
    response["trait"]["trait_id"] = trait_id
    response["trait"]["value"] = payload.get("delta", response["trait"]["value"])
    response["trait"]["version"] = payload.get("expected_version", response["trait"]["version"])
    return response


@app.post("/governance/check")
async def governance_check(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    response = copy.deepcopy(SAMPLE_PAYLOADS["governance"])
    signals = payload.get("signals") or {}
    drift_score = signals.get("drift_score", 0.0) if isinstance(signals, dict) else 0.0
    if drift_score >= 0.55:
        response["verdict"] = "block"
        response["issues"] = [{"code": "DRIFT", "severity": "high", "message": "Dérive critique"}]
    elif drift_score >= 0.35:
        response["verdict"] = "warn"
        response["issues"] = [{"code": "DRIFT", "severity": "medium", "message": "Dérive à surveiller"}]
    return response


@app.get("/metrics")
async def get_metrics(format: str = Query("json")) -> Dict[str, Any]:
    payload = copy.deepcopy(SAMPLE_PAYLOADS["metrics"])
    if format == "csv":
        raise HTTPException(status_code=501, detail="Mode CSV non mocké")
    return payload


@app.get("/openapi.yaml", include_in_schema=False)
async def download_openapi() -> Dict[str, Any]:
    return OPENAPI_SPEC


def main() -> None:
    uvicorn.run("mock_server.server:app", host="127.0.0.1", port=4600, reload=False)


if __name__ == "__main__":
    main()





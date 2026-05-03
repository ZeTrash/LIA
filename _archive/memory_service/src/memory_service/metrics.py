"""Instrumentation Prometheus."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

CONTEXT_LATENCY_MS = Histogram(
    "memory_service_context_latency_ms",
    "Latence de génération du paquet contexte (ms).",
    buckets=(25, 50, 75, 100, 150, 200, 300, 500, 750, 1000),
)

CONTEXT_PAYLOAD_BYTES = Histogram(
    "memory_service_context_payload_bytes",
    "Taille du paquet contexte (octets).",
    buckets=(1024, 2048, 4096, 6144, 8192, 10240, 14336),
)

INTERACTIONS_TOTAL = Counter(
    "memory_service_interactions_total",
    "Nombre total d'interactions journalisées.",
)

GOVERNANCE_DECISIONS = Counter(
    "memory_service_governance_decisions_total",
    "Décisions issues des garde-fous.",
    ["verdict"],
)

SOUVENIRS_GAUGE = Gauge(
    "memory_service_souvenirs_active",
    "Nombre de souvenirs actifs en base.",
)


def export_prometheus() -> tuple[bytes, str]:
    """Retourne le payload Prometheus + content-type."""

    return generate_latest(), CONTENT_TYPE_LATEST


def set_souvenirs_total(total: int) -> None:
    SOUVENIRS_GAUGE.set(total)




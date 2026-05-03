"""Script de validation d'intégration : compare le service réel au mock server."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml
from rich.console import Console
from rich.table import Table

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from memory_service.api import create_app
from memory_service.config import get_settings
from memory_service.schemas import (
    GovernanceCheckRequest,
    GovernanceSignal,
    InteractionDecisions,
    InteractionEmotions,
    InteractionRequest,
    InteractionScores,
    TraitUpdateRequest,
)
from fastapi.testclient import TestClient

console = Console()

BASE_DIR = Path(__file__).resolve().parents[2]
SPEC_PATH = BASE_DIR / "charge_timeline" / "etape1_cahier_charges" / "livrables" / "api_spec_openapi.yaml"
SAMPLES_PATH = BASE_DIR / "charge_timeline" / "etape1_cahier_charges" / "livrables" / "mock_server" / "sample_payloads.json"

with SPEC_PATH.open("r", encoding="utf-8") as f:
    OPENAPI_SPEC: Dict[str, Any] = yaml.safe_load(f)

with SAMPLES_PATH.open("r", encoding="utf-8") as f:
    SAMPLE_PAYLOADS: Dict[str, Any] = json.load(f)


def validate_context_endpoint(client: TestClient, session_id: str = "test-session") -> Dict[str, Any]:
    """Valide GET /context."""
    results = {"passed": [], "failed": []}

    response = client.get("/context", params={"session_id": session_id})
    if response.status_code != 200:
        results["failed"].append(f"Status code: {response.status_code} (attendu 200)")
        return results

    data = response.json()

    # Vérifier les champs requis
    required = ["traits", "session_goals", "memories", "indicators", "governance_metadata"]
    for field in required:
        if field in data:
            results["passed"].append(f"Champ requis '{field}' présent")
        else:
            results["failed"].append(f"Champ requis '{field}' manquant")

    # Vérifier la latence
    build_time = data.get("build_time_ms", 0)
    if build_time < 200:
        results["passed"].append(f"Latence OK: {build_time}ms < 200ms")
    else:
        results["failed"].append(f"Latence trop élevée: {build_time}ms >= 200ms")

    # Vérifier la taille du payload
    payload_bytes = len(response.content)
    if payload_bytes < 10240:
        results["passed"].append(f"Payload OK: {payload_bytes} bytes < 10KB")
    else:
        results["failed"].append(f"Payload trop volumineux: {payload_bytes} bytes >= 10KB")

    # Vérifier les métadonnées
    if "trace_id" in data:
        results["passed"].append("trace_id présent")
    else:
        results["failed"].append("trace_id manquant")

    if "context_checksum" in data:
        results["passed"].append("context_checksum présent")
    else:
        results["failed"].append("context_checksum manquant")

    return results


def validate_interaction_endpoint(client: TestClient) -> Dict[str, Any]:
    """Valide POST /interaction."""
    results = {"passed": [], "failed": []}

    payload = InteractionRequest(
        interaction_id="validate-i-001",
        session_id="test-session",
        prompt="Test prompt",
        response="Test response",
        scores=InteractionScores(usefulness=0.8, coherence=0.9, tone=0.9),
        emotions=InteractionEmotions(valence=0.3, arousal=0.4),
        decisions=InteractionDecisions(create_memory=True, derived_traits=["tone"]),
    )

    response = client.post("/interaction", json=payload.model_dump())
    if response.status_code != 200:
        results["failed"].append(f"Status code: {response.status_code} (attendu 200)")
        return results

    data = response.json()

    # Vérifier les champs
    required_fields = ["interaction_id", "session_id", "occurred_at", "severity"]
    for field in required_fields:
        if field in data:
            results["passed"].append(f"Champ '{field}' présent")
        else:
            results["failed"].append(f"Champ '{field}' manquant")

    # Vérifier l'idempotence
    response2 = client.post("/interaction", json=payload.model_dump())
    if response2.status_code == 200:
        data2 = response2.json()
        if data["interaction_id"] == data2["interaction_id"]:
            results["passed"].append("Idempotence vérifiée")
        else:
            results["failed"].append("Idempotence non respectée")

    return results


def validate_trait_update_endpoint(client: TestClient) -> Dict[str, Any]:
    """Valide POST /trait-update."""
    results = {"passed": [], "failed": []}

    payload = TraitUpdateRequest(
        trait_id="validate-trait",
        delta={"value": "test value", "weight": 0.8},
        reason="Validation test",
        source="script",
    )

    response = client.post("/trait-update", json=payload.model_dump())
    if response.status_code != 200:
        results["failed"].append(f"Status code: {response.status_code} (attendu 200)")
        return results

    data = response.json()

    # Vérifier la structure
    if "trait" in data:
        results["passed"].append("Champ 'trait' présent")
        if "version_token" in data:
            results["passed"].append("version_token présent")
        else:
            results["failed"].append("version_token manquant")
    else:
        results["failed"].append("Champ 'trait' manquant")

    return results


def validate_governance_endpoint(client: TestClient) -> Dict[str, Any]:
    """Valide POST /governance/check."""
    results = {"passed": [], "failed": []}

    # Test avec drift bloquant
    payload = GovernanceCheckRequest(
        session_id="test-session",
        draft_response="Réponse de test",
        signals=[GovernanceSignal(type="drift", value=0.6)],  # > 0.55
    )

    response = client.post("/governance/check", json=payload.model_dump())
    if response.status_code != 200:
        results["failed"].append(f"Status code: {response.status_code} (attendu 200)")
        return results

    data = response.json()

    if data.get("verdict") == "block":
        results["passed"].append("Drift bloquant détecté (verdict=block)")
    else:
        results["failed"].append(f"Drift bloquant non détecté (verdict={data.get('verdict')})")

    # Test avec drift modéré
    payload2 = GovernanceCheckRequest(
        session_id="test-session",
        draft_response="Réponse",
        signals=[GovernanceSignal(type="drift", value=0.4)],  # Entre 0.35 et 0.55
    )
    response2 = client.post("/governance/check", json=payload2.model_dump())
    if response2.status_code == 200:
        data2 = response2.json()
        if data2.get("verdict") == "warn":
            results["passed"].append("Drift modéré détecté (verdict=warn)")
        else:
            results["failed"].append(f"Drift modéré non détecté (verdict={data2.get('verdict')})")

    return results


def validate_metrics_endpoint(client: TestClient) -> Dict[str, Any]:
    """Valide GET /metrics."""
    results = {"passed": [], "failed": []}

    response = client.get("/metrics")
    if response.status_code != 200:
        results["failed"].append(f"Status code: {response.status_code} (attendu 200)")
        return results

    data = response.json()

    # Vérifier les KPI
    if "kpis" in data:
        kpis = data["kpis"]
        required_kpis = [
            "latency_context_ms",
            "context_payload_bytes",
            "coherence_score",
            "drift_alerts_count",
            "ttl_purge_rate",
            "store_availability",
        ]
        for kpi in required_kpis:
            if kpi in kpis:
                results["passed"].append(f"KPI '{kpi}' présent")
            else:
                results["failed"].append(f"KPI '{kpi}' manquant")
    else:
        results["failed"].append("Champ 'kpis' manquant")

    # Vérifier Prometheus
    prom_response = client.get("/metrics/prom")
    if prom_response.status_code == 200:
        if "memory_service_context_latency_ms" in prom_response.text:
            results["passed"].append("Endpoint Prometheus fonctionnel")
        else:
            results["failed"].append("Endpoint Prometheus ne retourne pas les métriques attendues")
    else:
        results["failed"].append(f"Endpoint Prometheus: status {prom_response.status_code}")

    return results


def main():
    """Exécute la validation complète."""
    console.print("[bold blue]Validation d'intégration du service mémoire[/bold blue]\n")

    # Créer le client de test
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["MEMORY_SERVICE_DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["MEMORY_SERVICE_DATA_DIR"] = tmpdir
        get_settings.cache_clear()

        app = create_app()
        client = TestClient(app)

        # Exécuter les validations
        all_results: Dict[str, Dict[str, List[str]]] = {}

        console.print("[cyan]1. Validation GET /context[/cyan]")
        all_results["GET /context"] = validate_context_endpoint(client)
        console.print(f"   ✓ {len(all_results['GET /context']['passed'])} tests passés")
        console.print(f"   ✗ {len(all_results['GET /context']['failed'])} tests échoués")

        console.print("\n[cyan]2. Validation POST /interaction[/cyan]")
        all_results["POST /interaction"] = validate_interaction_endpoint(client)
        console.print(f"   ✓ {len(all_results['POST /interaction']['passed'])} tests passés")
        console.print(f"   ✗ {len(all_results['POST /interaction']['failed'])} tests échoués")

        console.print("\n[cyan]3. Validation POST /trait-update[/cyan]")
        all_results["POST /trait-update"] = validate_trait_update_endpoint(client)
        console.print(f"   ✓ {len(all_results['POST /trait-update']['passed'])} tests passés")
        console.print(f"   ✗ {len(all_results['POST /trait-update']['failed'])} tests échoués")

        console.print("\n[cyan]4. Validation POST /governance/check[/cyan]")
        all_results["POST /governance/check"] = validate_governance_endpoint(client)
        console.print(f"   ✓ {len(all_results['POST /governance/check']['passed'])} tests passés")
        console.print(f"   ✗ {len(all_results['POST /governance/check']['failed'])} tests échoués")

        console.print("\n[cyan]5. Validation GET /metrics[/cyan]")
        all_results["GET /metrics"] = validate_metrics_endpoint(client)
        console.print(f"   ✓ {len(all_results['GET /metrics']['passed'])} tests passés")
        console.print(f"   ✗ {len(all_results['GET /metrics']['failed'])} tests échoués")

        # Résumé
        console.print("\n[bold]Résumé de la validation[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Endpoint")
        table.add_column("Passés", justify="right")
        table.add_column("Échoués", justify="right")
        table.add_column("Statut")

        total_passed = 0
        total_failed = 0

        for endpoint, results in all_results.items():
            passed = len(results["passed"])
            failed = len(results["failed"])
            total_passed += passed
            total_failed += failed
            status = "✅ OK" if failed == 0 else "⚠️  ÉCHECS"
            table.add_row(endpoint, str(passed), str(failed), status)

        table.add_row("[bold]TOTAL[/bold]", f"[bold]{total_passed}[/bold]", f"[bold]{total_failed}[/bold]", "")

        console.print(table)

        # Afficher les détails des échecs
        if total_failed > 0:
            console.print("\n[bold red]Détails des échecs:[/bold red]")
            for endpoint, results in all_results.items():
                if results["failed"]:
                    console.print(f"\n[red]{endpoint}:[/red]")
                    for failure in results["failed"]:
                        console.print(f"  - {failure}")

        # Conclusion
        if total_failed == 0:
            console.print("\n[bold green]✅ Tous les tests d'intégration sont passés ![/bold green]")
            return 0
        else:
            console.print(f"\n[bold yellow]⚠️  {total_failed} test(s) ont échoué. Vérifiez les détails ci-dessus.[/bold yellow]")
            return 1


if __name__ == "__main__":
    try:
        from rich import console
    except ImportError:
        print("Installation de rich pour l'affichage...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
        from rich import console

    sys.exit(main())




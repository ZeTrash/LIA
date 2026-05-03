"""Script pour exécuter tous les tests des services."""

import subprocess
import sys
from pathlib import Path

def run_tests(service_name: str, test_path: str) -> tuple[bool, str]:
    """Exécute les tests d'un service et retourne le résultat."""
    print(f"\n{'='*60}")
    print(f"Tests du service: {service_name}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    output = result.stdout + result.stderr
    success = result.returncode == 0
    
    print(output)
    return success, output

def main():
    """Exécute tous les tests."""
    print("="*60)
    print("EXÉCUTION DE TOUS LES TESTS")
    print("="*60)
    
    results = []
    
    # Tests memory_service (Étape 1)
    success1, output1 = run_tests(
        "memory_service (Étape 1)",
        "memory_service/tests/test_integration.py"
    )
    results.append(("memory_service", success1))
    
    # Tests simulation_service (Étape 2)
    success2, output2 = run_tests(
        "simulation_service (Étape 2)",
        "simulation_service/tests/"
    )
    results.append(("simulation_service", success2))
    
    # Résumé final
    print("\n" + "="*60)
    print("RÉSUMÉ FINAL")
    print("="*60)
    
    for service, success in results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
        print(f"{service:30} : {status}")
    
    total_success = sum(1 for _, success in results if success)
    print(f"\nTotal: {total_success}/{len(results)} services avec tests réussis")
    
    return 0 if all(success for _, success in results) else 1

if __name__ == "__main__":
    sys.exit(main())




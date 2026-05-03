"""Script pour lancer les tests du service de simulation."""

import sys
import subprocess
from pathlib import Path

def main():
    """Lance les tests avec pytest."""
    # S'assurer qu'on est dans le bon répertoire
    test_dir = Path(__file__).parent / "tests"
    src_dir = Path(__file__).parent / "src"
    
    if not test_dir.exists():
        print(f"❌ Le dossier tests/ n'existe pas: {test_dir}")
        return 1
    
    print("🧪 Lancement des tests...")
    print(f"📁 Répertoire: {Path(__file__).parent}")
    print(f"📁 Tests: {test_dir}")
    print(f"📁 Source: {src_dir}")
    print()
    
    # Configurer PYTHONPATH
    import os
    env = dict(os.environ)
    pythonpath = str(src_dir)
    if 'PYTHONPATH' in env:
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env['PYTHONPATH'] = pythonpath
    
    # Lancer pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=Path(__file__).parent,
        env=env
    )
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())



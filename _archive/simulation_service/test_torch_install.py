"""Script pour tester l'installation de torch."""
import sys

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")

try:
    import torch
    print(f"✅ torch installé - version: {torch.__version__}")
except ImportError as e:
    print(f"❌ torch NON installé: {e}")
    print("\nTentative d'installation...")
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pip", "install", "torch", "transformers", "accelerate"], 
                          capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
    
    # Réessayer l'import
    try:
        import torch
        print(f"✅ torch installé après tentative - version: {torch.__version__}")
    except ImportError as e2:
        print(f"❌ Échec final: {e2}")

try:
    import transformers
    print(f"✅ transformers installé - version: {transformers.__version__}")
except ImportError as e:
    print(f"❌ transformers NON installé: {e}")

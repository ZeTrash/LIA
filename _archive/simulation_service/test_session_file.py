"""Test pour vérifier le chemin du fichier de session."""

import sys
from pathlib import Path

# Ajouter src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simulation_service.cli import get_last_session_file

f = get_last_session_file()
print(f"📁 Fichier de session: {f.absolute()}")
print(f"📂 Répertoire: {f.parent}")
print(f"✅ Existe: {f.exists()}")
if f.exists():
    print(f"📄 Contenu: {f.read_text()}")



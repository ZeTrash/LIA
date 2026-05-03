"""Seed des thèmes de patterns (V2).

À exécuter après migrate_patterns_v2.py pour peupler les thèmes initiaux.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service import MemoryAdapter  # type: ignore

THEMES_INITIAUX = [
    "no_pattern",   # Pattern par défaut (clear_memory_db)
    "salutation",
    "mémoire",
    "identité",
    "identité_utilisateur",
    "question",
    "autre",
]


def init_theme_patterns() -> None:
    print("=" * 70)
    print("🔧 Seed des thèmes de patterns (V2)")
    print("=" * 70)
    print()

    memory = MemoryAdapter()

    for theme in THEMES_INITIAUX:
        try:
            tid = memory.add_theme_pattern(theme)
            print(f"✅ Thème seed: {theme} (id={tid})")
        except Exception as e:
            print(f"ℹ️  Thème {theme}: déjà existant ou erreur - {e}")

    print()
    themes = memory.list_theme_patterns()
    print(f"🎯 Thèmes disponibles: {themes}")
    print()


if __name__ == "__main__":
    init_theme_patterns()


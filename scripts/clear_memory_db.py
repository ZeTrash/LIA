"""Script pour vider la base mémoire sans supprimer les tables.

Objectif:
- Supprimer tous les enregistrements (lignes) des tables SQLite utilisées par LIA,
  en conservant la structure de la base (tables, colonnes, index).

Utilisation:
    cd /opt/LIA
    source venv/bin/activate
    python3 scripts/clear_memory_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import MetaData

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service.db import get_db  # type: ignore
from memory_service import MemoryAdapter  # type: ignore


def clear_all_tables(dry_run: bool = False) -> None:
    """Supprime toutes les lignes de toutes les tables connues.

    Ne supprime PAS les tables elles-mêmes.
    """
    db = get_db()
    engine = db.engine

    metadata = MetaData()
    metadata.reflect(bind=engine)

    if not metadata.tables:
        print("❌ Aucune table trouvée dans la base.")
        return

    print(f"Base cible : {db.db_path}")
    print("Tables détectées :")
    for name in metadata.tables:
        print(f"  - {name}")

    if dry_run:
        print("\nMode dry-run: aucune suppression effectuée.")
        return

    with engine.begin() as conn:
        # On supprime dans l'ordre inverse pour respecter les contraintes FK éventuelles
        for table in reversed(metadata.sorted_tables):
            print(f"🧹 DELETE FROM {table.name} ...", end="", flush=True)
            conn.execute(table.delete())
            print(" OK")

    print("\n✅ Toutes les tables ont été vidées (structure conservée).")

    # Seed d'un pattern de base (theme_pattern "no_pattern" pour patterns par défaut)
    try:
        memory = MemoryAdapter()
        if hasattr(memory, "add_theme_pattern"):
            try:
                memory.add_theme_pattern("no_pattern")
            except Exception:
                pass
        pid = memory.upsert_pattern(
            menu_context="base",
            prev_step="initial",
            recommended_step="B3",
            weights={"B3": 1.0},
            source="seed_clear_db",
            confidence=0.5,
            theme_pattern="no_pattern",
        )
        print(f"🎯 Pattern de base seedé: theme=no_pattern, ctx=base, prev=initial, rec=B3, id={pid}")
    except Exception as e:
        print(f"⚠️  Impossible de seeder le pattern de base après vidage: {e}")


if __name__ == "__main__":
    clear_all_tables(dry_run=False)



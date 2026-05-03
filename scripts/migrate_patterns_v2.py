"""Migration V2 : ajoute theme_patterns et la colonne theme_pattern à patterns.

À exécuter une fois pour les bases existantes.
Pour les nouvelles installations, create_all crée tout automatiquement.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from memory_service.db import get_db
from memory_service.models import ThemePatternModel


def migrate() -> None:
    db = get_db()
    engine = db.engine

    # Créer la table theme_patterns si elle n'existe pas
    ThemePatternModel.__table__.create(engine, checkfirst=True)

    # Ajouter la colonne theme_pattern à patterns si elle n'existe pas (SQLite)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM pragma_table_info('patterns') WHERE name='theme_pattern'")
        )
        count = result.scalar()
        if count == 0:
            conn.execute(text("ALTER TABLE patterns ADD COLUMN theme_pattern VARCHAR"))
            conn.commit()
            print("✅ Colonne theme_pattern ajoutée à la table patterns.")
        else:
            print("ℹ️  Colonne theme_pattern déjà présente.")

    print("✅ Migration V2 terminée.")


if __name__ == "__main__":
    migrate()


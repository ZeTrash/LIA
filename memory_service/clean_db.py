"""Script pour nettoyer la base de données mémoire."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service.db import Database
from memory_service.models import TraitModel, SouvenirModel, InteractionModel
from sqlalchemy.orm import Session


def clean_database(db_path: str = "data/memory.db", confirm: bool = False):
    """
    Nettoie la base de données en supprimant toutes les données.
    
    Args:
        db_path: Chemin vers la base de données
        confirm: Si False, demande confirmation avant de supprimer
    """
    db = Database(db_path=db_path)
    session = db.get_session()
    
    try:
        # Compter les données avant suppression
        traits_count = session.query(TraitModel).count()
        memories_count = session.query(SouvenirModel).count()
        interactions_count = session.query(InteractionModel).count()
        
        print("=" * 60)
        print("Nettoyage de la base de données mémoire")
        print("=" * 60)
        print()
        print(f"Données actuelles :")
        print(f"  - Traits : {traits_count}")
        print(f"  - Souvenirs : {memories_count}")
        print(f"  - Interactions : {interactions_count}")
        print()
        
        if not confirm:
            response = input("Voulez-vous vraiment supprimer toutes ces données ? (oui/non): ")
            if response.lower() not in ['oui', 'o', 'yes', 'y']:
                print("Opération annulée.")
                return
        
        # Supprimer toutes les données
        print("Suppression des données...")
        session.query(InteractionModel).delete()
        session.query(SouvenirModel).delete()
        session.query(TraitModel).delete()
        session.commit()
        
        print("✅ Base de données nettoyée avec succès !")
        print()
        print("La base de données est maintenant vide et prête pour la phase suivante.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erreur lors du nettoyage : {e}")
        raise
    finally:
        session.close()
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Nettoyer la base de données mémoire")
    parser.add_argument(
        "--db-path",
        default="data/memory.db",
        help="Chemin vers la base de données (défaut: data/memory.db)"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Supprimer sans demander confirmation"
    )
    
    args = parser.parse_args()
    
    clean_database(db_path=args.db_path, confirm=args.yes)


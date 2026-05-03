#!/usr/bin/env python3
"""
Script de migration pour ajouter la colonne memory_rank_score à la table souvenirs.

Ce script est nécessaire si vous avez une base de données créée avant l'ajout de MemoryRank.
Il ajoute la colonne memory_rank_score avec une valeur par défaut de 0.0.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service.db import Database, get_db
from memory_service.models import Base
from sqlalchemy import text

def migrate_add_memory_rank_score():
    """Ajoute la colonne memory_rank_score à la table souvenirs et crée les tables MemoryRank si nécessaire."""
    print("=" * 70)
    print("🔧 Migration : Ajout de memory_rank_score et tables MemoryRank")
    print("=" * 70)
    print()
    
    try:
        db = get_db()
        engine = db.engine
        
        # Étape 1 : Créer toutes les tables si elles n'existent pas (y compris memory_links)
        print("ℹ Étape 1 : Vérification et création des tables nécessaires...")
        Base.metadata.create_all(engine)
        print("✅ Toutes les tables sont à jour.")
        print()
        
        # Étape 2 : Ajouter memory_rank_score à souvenirs si nécessaire
        print("ℹ Étape 2 : Vérification de la colonne memory_rank_score...")
        with engine.connect() as conn:
            # Vérifier si la colonne existe déjà
            result = conn.execute(text("PRAGMA table_info(souvenirs)"))
            columns = [row[1] for row in result]
            
            if 'memory_rank_score' in columns:
                print("✅ La colonne memory_rank_score existe déjà.")
                print("   Aucune migration nécessaire pour cette colonne.")
            else:
                print(f"ℹ Colonnes actuelles : {', '.join(columns)}")
                print()
                print("ℹ Ajout de la colonne memory_rank_score...")
                
                # Ajouter la colonne
                conn.execute(text("""
                    ALTER TABLE souvenirs 
                    ADD COLUMN memory_rank_score REAL DEFAULT 0.0
                """))
                conn.commit()
                
                print("✅ Colonne memory_rank_score ajoutée avec succès.")
            
            print()
            
            # Vérifier que la colonne est présente
            result = conn.execute(text("PRAGMA table_info(souvenirs)"))
            columns_after = [row[1] for row in result]
            
            if 'memory_rank_score' in columns_after:
                print("✅ Vérification : La colonne memory_rank_score est présente.")
                
                # Compter les souvenirs existants
                count_result = conn.execute(text("SELECT COUNT(*) FROM souvenirs"))
                count = count_result.scalar()
                print(f"ℹ Nombre de souvenirs existants : {count}")
                if count > 0:
                    print(f"   Tous ont maintenant memory_rank_score = 0.0 par défaut.")
                print()
                
                # Vérifier la table memory_links
                print("ℹ Étape 3 : Vérification de la table memory_links...")
                try:
                    links_result = conn.execute(text("SELECT COUNT(*) FROM memory_links"))
                    links_count = links_result.scalar()
                    print(f"✅ Table memory_links existe ({links_count} liens).")
                except Exception as e:
                    print(f"⚠️ Table memory_links non trouvée, sera créée automatiquement.")
                    Base.metadata.create_all(engine)
                    print("✅ Table memory_links créée.")
                
                print()
                print("💡 Pour calculer les scores MemoryRank, utilisez :")
                print("   from memory_service.memory_rank_engine import MemoryRankEngine")
                print("   engine = MemoryRankEngine()")
                print("   engine.compute_and_update_ranks()")
            else:
                print("⚠️ Erreur : La colonne n'a pas été ajoutée correctement.")
                return False
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_add_memory_rank_score()
    sys.exit(0 if success else 1)


"""Gestion de la base de données SQLite pour la mémoire."""

import logging
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

logger = logging.getLogger(__name__)


class Database:
    """Gestionnaire de base de données."""
    
    def __init__(self, db_path: str = "data/memory.db"):
        """
        Initialise la base de données.
        
        Args:
            db_path: Chemin vers le fichier SQLite
        """
        # IMPORTANT: rendre le chemin stable, indépendant du cwd (web_interface vs repo root).
        # Sinon on crée plusieurs DB différentes: /opt/LIA/data/memory.db et /opt/LIA/web_interface/data/memory.db
        env_path = os.environ.get("LIA_MEMORY_DB_PATH")
        effective_path = env_path or db_path

        p = Path(effective_path)
        if not p.is_absolute():
            project_root = Path(__file__).resolve().parent.parent  # /opt/LIA
            p = project_root / p

        self.db_path = p
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Créer l'engine SQLite avec WAL activé
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        
        # Créer les tables
        Base.metadata.create_all(self.engine)
        
        # Créer la session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=self.engine
        )
        
        logger.info(f"Base de données initialisée: {self.db_path}")
    
    def get_session(self) -> Session:
        """Retourne une nouvelle session de base de données."""
        return self.SessionLocal()
    
    def close(self):
        """Ferme la connexion à la base de données."""
        self.engine.dispose()
        logger.info("Base de données fermée")


# Instance globale
_db_instance: Database | None = None


def get_db() -> Database:
    """Retourne l'instance globale de la base de données."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


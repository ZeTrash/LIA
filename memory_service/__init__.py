"""Service mémoire de LIA - Persistance et personnalité."""

__version__ = "0.1.0"

from .models import TraitModel, SouvenirModel, InteractionModel, PatternModel, Base
from .db import Database, get_db
from .store import MemoryStore
from .memory_adapter import MemoryAdapter
from .autonomy_store import AutonomyStore
from .api import app

__all__ = [
    "TraitModel",
    "SouvenirModel",
    "InteractionModel",
    "PatternModel",
    "Base",
    "Database",
    "get_db",
    "MemoryStore",
    "MemoryAdapter",
    "AutonomyStore",
    "app",
]


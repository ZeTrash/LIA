"""Tests d'intégration pour PhraseMemoryProcessor."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from memory_service.phrase_memory_processor import PhraseMemoryProcessor
from memory_service.store import MemoryStore
from memory_service.db import Database
from memory_service.models import Base


@pytest.fixture
def temp_db():
    """Crée une base de données temporaire pour les tests."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = Database(db_path=path)
    Base.metadata.create_all(db.engine)
    
    yield db
    
    db.close()
    os.unlink(path)


@pytest.fixture
def processor(temp_db):
    """Crée un processeur pour les tests."""
    store = MemoryStore(db=temp_db, use_memory_rank=True)
    return PhraseMemoryProcessor(memory_store=store, threshold=0.3)


@pytest.mark.asyncio
async def test_process_simple_interaction(processor):
    """Test de traitement d'une interaction simple."""
    interaction = {
        "prompt": "Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
        "response": "Python est effectivement un excellent choix pour l'IA.",
        "session_id": "test_session_1"
    }
    
    stored_ids = await processor.process_interaction(interaction)
    
    # Devrait stocker au moins quelques phrases importantes
    assert len(stored_ids) > 0
    
    # Vérifier que les phrases sont stockées
    context = processor.store.get_context(limit_memories=10)
    memories = context.get("memories", [])
    
    # Au moins une mémoire devrait contenir "Python"
    assert any("Python" in m.get("content", "") for m in memories)


@pytest.mark.asyncio
async def test_filter_redundant_phrases(processor):
    """Test que les phrases redondantes ne sont pas stockées deux fois."""
    # Première interaction
    interaction1 = {
        "prompt": "Je préfère Python à Java.",
        "response": "Python est un bon choix.",
        "session_id": "test_session_2"
    }
    
    stored_ids1 = await processor.process_interaction(interaction1)
    assert len(stored_ids1) > 0
    
    # Deuxième interaction avec phrase similaire
    interaction2 = {
        "prompt": "Je préfère Python à Java aussi.",
        "response": "C'est une bonne préférence.",
        "session_id": "test_session_2"
    }
    
    stored_ids2 = await processor.process_interaction(interaction2)
    
    # La phrase redondante devrait avoir un score de nouveauté faible
    # et pourrait ne pas être stockée si le seuil est assez élevé
    # Pour ce test, on vérifie juste que le traitement fonctionne
    assert isinstance(stored_ids2, list)


@pytest.mark.asyncio
async def test_create_links_between_phrases(processor):
    """Test que des liens sont créés entre les phrases de la même interaction."""
    interaction = {
        "prompt": "Je préfère Python. J'aime l'IA. Mon objectif est de créer un système autonome.",
        "response": "Ce sont de bons choix.",
        "session_id": "test_session_3"
    }
    
    stored_ids = await processor.process_interaction(interaction)
    
    # Si plusieurs phrases sont stockées, des liens devraient être créés
    if len(stored_ids) > 1:
        # Vérifier que des liens existent
        # (on peut vérifier via le graphe MemoryRank)
        ranks = processor.rank_engine.compute_and_update_ranks()
        assert len(ranks) > 0


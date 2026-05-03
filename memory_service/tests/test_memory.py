"""Tests pour le service mémoire."""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory_service.models import TraitModel, SouvenirModel, InteractionModel
from memory_service.db import Database
from memory_service.store import MemoryStore


@pytest.fixture
def temp_db():
    """Crée une base de données temporaire pour les tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = Database(db_path=db_path)
    yield db
    db.close()
    os.unlink(db_path)


@pytest.fixture
def store(temp_db):
    """Crée un store avec une base de données temporaire."""
    # Créer un store avec la base de données temporaire
    # Cela teste le comportement réel sans contourner le système
    store = MemoryStore(db=temp_db)
    
    yield store


def test_add_trait(store):
    """Test d'ajout d'un trait."""
    trait_id = store.add_trait(
        trait_type="persona",
        label="curiosité",
        value="très curieux",
        weight=0.9,
        confidence=0.8
    )
    
    assert trait_id is not None
    
    # Vérifier que le trait existe
    context = store.get_context()
    traits = [t for t in context["traits"] if t["trait_id"] == trait_id]
    assert len(traits) == 1
    assert traits[0]["label"] == "curiosité"
    assert traits[0]["value"] == "très curieux"


def test_add_memory(store):
    """Test d'ajout d'un souvenir."""
    memory_id = store.add_memory(
        category="fact",
        content="L'utilisateur aime le café",
        tags=["préférence", "boisson"],
        importance_score=0.7
    )
    
    assert memory_id is not None
    
    # Vérifier que le souvenir existe
    context = store.get_context()
    memories = [m for m in context["memories"] if m["memory_id"] == memory_id]
    assert len(memories) == 1
    assert memories[0]["content"] == "L'utilisateur aime le café"
    assert memories[0]["category"] == "fact"


def test_log_interaction(store):
    """Test de journalisation d'une interaction."""
    interaction_id = store.log_interaction(
        session_id="test_session",
        prompt="Bonjour",
        response="Bonjour ! Comment puis-je vous aider ?",
        severity="info"
    )
    
    assert interaction_id is not None


def test_get_context(store):
    """Test de récupération du contexte."""
    # Ajouter quelques données
    store.add_trait("persona", "amabilité", "très amical", 0.8)
    store.add_memory("preference", "Aime les chats", ["animaux"], 0.6)
    
    context = store.get_context()
    
    assert "traits" in context
    assert "memories" in context
    assert "session_goals" in context
    assert len(context["traits"]) >= 1
    assert len(context["memories"]) >= 1


def test_update_trait(store):
    """Test de mise à jour d'un trait existant."""
    # Créer un trait
    trait_id = store.add_trait("persona", "curiosité", "curieux", 0.5)
    
    # Mettre à jour le trait (même label et type)
    updated_id = store.add_trait("persona", "curiosité", "très curieux", 0.9)
    
    # L'ID doit être le même (mise à jour)
    assert trait_id == updated_id
    
    # Vérifier que la valeur a été mise à jour
    context = store.get_context()
    traits = [t for t in context["traits"] if t["trait_id"] == trait_id]
    assert len(traits) == 1
    assert traits[0]["value"] == "très curieux"
    assert traits[0]["weight"] == 0.9


def test_log_interaction_persistence(store):
    """Test que les interactions sont bien persistées."""
    interaction_id = store.log_interaction(
        session_id="test_session",
        prompt="Test prompt",
        response="Test response",
        severity="info"
    )
    
    assert interaction_id is not None
    
    # Vérifier que l'interaction existe en base
    session = store.db.get_session()
    try:
        interaction = session.query(InteractionModel).filter(
            InteractionModel.interaction_id == interaction_id
        ).first()
        
        assert interaction is not None
        assert interaction.prompt == "Test prompt"
        assert interaction.response == "Test response"
        assert interaction.session_id == "test_session"
        assert interaction.severity == "info"
    finally:
        session.close()


def test_context_limits(store):
    """Test que les limites de contexte sont respectées."""
    # Ajouter plus de traits que la limite
    for i in range(15):
        store.add_trait("persona", f"trait_{i}", f"value_{i}", 0.5)
    
    # Récupérer avec limite de 5
    context = store.get_context(limit_traits=5, limit_memories=5)
    
    assert len(context["traits"]) == 5
    assert len(context["memories"]) <= 5


def test_memory_tags(store):
    """Test que les tags des souvenirs sont correctement gérés."""
    memory_id = store.add_memory(
        category="fact",
        content="Test avec tags",
        tags=["tag1", "tag2", "tag3"],
        importance_score=0.8
    )
    
    context = store.get_context()
    memories = [m for m in context["memories"] if m["memory_id"] == memory_id]
    
    assert len(memories) == 1
    assert "tag1" in memories[0]["tags"]
    assert "tag2" in memories[0]["tags"]
    assert "tag3" in memories[0]["tags"]


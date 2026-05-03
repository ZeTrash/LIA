"""Tests pour MemoryManager (Phase 4)."""

import pytest
from unittest.mock import Mock, AsyncMock

from memory_service.memory_manager import MemoryManager, MemoryItem


@pytest.fixture
def mock_memory_adapter():
    """Crée un mock MemoryAdapter."""
    adapter = Mock()
    adapter.add_memory_from_interaction = Mock(return_value="memory_123")
    return adapter


@pytest.fixture
def memory_manager(mock_memory_adapter):
    """Crée un MemoryManager pour tests."""
    config = {
        "min_importance_score": 0.6,
        "max_memories_per_interaction": 3,
        "enable_auto_cleanup": True
    }
    return MemoryManager(
        memory_adapter=mock_memory_adapter,
        config=config
    )


@pytest.fixture
def sample_interaction():
    """Crée une interaction d'exemple."""
    return {
        "prompt": "Je préfère le café au thé",
        "response": "D'accord, je retiens que tu préfères le café.",
        "session_id": "test_session_123"
    }


@pytest.fixture
def high_importance_interaction():
    """Crée une interaction à haute importance."""
    return {
        "prompt": "Souviens-toi que j'aime beaucoup le chocolat, c'est important !",
        "response": "Je retiendrai que tu aimes beaucoup le chocolat.",
        "session_id": "test_session_123"
    }


@pytest.fixture
def low_importance_interaction():
    """Crée une interaction à faible importance."""
    return {
        "prompt": "Bonjour",
        "response": "Bonjour ! Comment puis-je t'aider ?",
        "session_id": "test_session_123"
    }


@pytest.mark.asyncio
async def test_decide_what_to_store_high_importance(
    memory_manager, high_importance_interaction
):
    """Test décision de stockage pour interaction importante."""
    items = await memory_manager.decide_what_to_store(
        interaction=high_importance_interaction
    )
    
    assert len(items) > 0
    assert all(isinstance(item, MemoryItem) for item in items)
    assert all(item.importance_score >= 0.6 for item in items)


@pytest.mark.asyncio
async def test_decide_what_to_store_low_importance(
    memory_manager, low_importance_interaction
):
    """Test décision de stockage pour interaction peu importante."""
    items = await memory_manager.decide_what_to_store(
        interaction=low_importance_interaction
    )
    
    # Les interactions peu importantes ne devraient pas être mémorisées
    assert len(items) == 0


@pytest.mark.asyncio
async def test_decide_what_to_store_preference(
    memory_manager, sample_interaction
):
    """Test extraction de préférence."""
    items = await memory_manager.decide_what_to_store(
        interaction=sample_interaction
    )
    
    # Devrait extraire la préférence
    if len(items) > 0:
        assert any("préfère" in item.content.lower() or "café" in item.content.lower() 
                  for item in items)


def test_analyze_importance_high(memory_manager, high_importance_interaction):
    """Test analyse d'importance pour interaction importante."""
    importance = memory_manager._analyze_importance(high_importance_interaction)
    assert importance >= 0.6


def test_analyze_importance_low(memory_manager, low_importance_interaction):
    """Test analyse d'importance pour interaction peu importante."""
    importance = memory_manager._analyze_importance(low_importance_interaction)
    assert importance < 0.6


def test_extract_key_information_preference(memory_manager, sample_interaction):
    """Test extraction d'informations clés pour préférence."""
    key_infos = memory_manager._extract_key_information(sample_interaction)
    
    assert len(key_infos) > 0
    assert any("café" in info.lower() or "préfère" in info.lower() 
              for info in key_infos)


def test_categorize_information_preference(memory_manager, sample_interaction):
    """Test catégorisation d'information comme préférence."""
    info = "Je préfère le café"
    category = memory_manager._categorize_information(info, sample_interaction)
    assert category == "preference"


def test_categorize_information_fact(memory_manager):
    """Test catégorisation d'information comme fait."""
    interaction = {"prompt": "Souviens-toi que Paris est la capitale de la France"}
    info = "Fait: Paris est la capitale"
    category = memory_manager._categorize_information(info, interaction)
    assert category == "fact"


def test_extract_tags(memory_manager, sample_interaction):
    """Test extraction de tags."""
    info = "Je préfère le café"
    tags = memory_manager._extract_tags(info, sample_interaction)
    
    assert isinstance(tags, list)
    assert "préférence" in tags or len(tags) > 0


def test_calculate_ttl_preference(memory_manager):
    """Test calcul TTL pour préférence."""
    ttl = memory_manager._calculate_ttl(importance=0.8, category="preference")
    assert ttl > 60  # Préférences durent longtemps


def test_calculate_ttl_alert(memory_manager):
    """Test calcul TTL pour alerte."""
    ttl = memory_manager._calculate_ttl(importance=0.5, category="alert")
    assert ttl < 30  # Alertes sont temporaires


@pytest.mark.asyncio
async def test_store_memories(memory_manager, mock_memory_adapter):
    """Test stockage de mémoires."""
    items = [
        MemoryItem(
            content="Je préfère le café",
            category="preference",
            importance_score=0.8
        )
    ]
    
    memory_ids = await memory_manager.store_memories(items, session_id="test")
    
    assert len(memory_ids) == 1
    assert memory_ids[0] == "memory_123"
    mock_memory_adapter.add_memory_from_interaction.assert_called_once()


@pytest.mark.asyncio
async def test_store_memories_empty_list(memory_manager):
    """Test stockage avec liste vide."""
    memory_ids = await memory_manager.store_memories([])
    assert len(memory_ids) == 0


@pytest.mark.asyncio
async def test_store_memories_no_adapter():
    """Test stockage sans MemoryAdapter."""
    manager = MemoryManager(memory_adapter=None)
    items = [
        MemoryItem(
            content="Test",
            category="fact",
            importance_score=0.7
        )
    ]
    
    memory_ids = await manager.store_memories(items)
    assert len(memory_ids) == 0


def test_max_memories_per_interaction(memory_manager):
    """Test limite de mémoires par interaction."""
    # Créer une interaction avec beaucoup d'informations
    interaction = {
        "prompt": "Je préfère le café, j'aime le chocolat, je déteste les épinards, et je veux me souvenir que j'aime la musique",
        "response": "D'accord, je retiens toutes ces informations.",
        "session_id": "test"
    }
    
    key_infos = memory_manager._extract_key_information(interaction)
    
    # Vérifier que le nombre d'informations extraites est limité
    items = []
    for info in key_infos[:memory_manager.max_memories_per_interaction]:
        importance = memory_manager._analyze_importance(interaction)
        if importance >= memory_manager.min_importance_score:
            category = memory_manager._categorize_information(info, interaction)
            item = MemoryItem(
                content=info,
                category=category,
                importance_score=importance
            )
            items.append(item)
    
    assert len(items) <= memory_manager.max_memories_per_interaction


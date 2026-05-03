"""Tests pour SemanticSearcher."""

import pytest
from datetime import datetime, timedelta, UTC

from memory_service.db import Database
from memory_service.models import Base, SouvenirModel
from memory_service.store import MemoryStore
from core.semantic_searcher import SemanticSearcher


@pytest.fixture
def test_db(tmp_path):
    """Crée une base de données temporaire pour les tests."""
    db_path = tmp_path / "test_semantic.db"
    db = Database(str(db_path))
    Base.metadata.create_all(db.engine)
    yield db
    db.close()


@pytest.fixture
def store(test_db):
    """Crée un MemoryStore pour les tests."""
    return MemoryStore(db=test_db, use_memory_rank=True)


@pytest.fixture
def searcher(store):
    """Crée un SemanticSearcher pour les tests."""
    return SemanticSearcher(memory_store=store)


@pytest.fixture
def sample_memories(store):
    """Crée des souvenirs de test pour la recherche sémantique."""
    now = datetime.now(UTC)
    ttl = now + timedelta(days=30)
    session = store.db.get_session()
    try:
        data = [
            ("Je suis LIA, un assistant IA autonome.", 0.8),
            ("J'aide les utilisateurs avec leurs projets Python.", 0.7),
            ("J'aime travailler sur des systèmes de mémoire avancés.", 0.6),
        ]
        for idx, (content, rank) in enumerate(data):
            mem = SouvenirModel(
                memory_id=f"s_{idx}",
                category="fact",
                content=content,
                tags=None,
                importance_score=0.7,
                recency_score=1.0,
                emotion_score=0.0,
                memory_rank_score=rank,
                frequency=1,
                ttl=ttl,
                created_at=now,
                updated_at=now,
            )
            session.add(mem)
        session.commit()
    finally:
        session.close()


def test_search_basic(searcher, sample_memories):
    """Vérifie qu'une recherche renvoie des résultats triés par score."""
    results = searcher.search(query="assistant IA", limit=5)
    assert len(results) > 0
    assert "search_score" in results[0]
    assert results[0]["search_score"] >= results[-1]["search_score"]


def test_search_with_category(searcher, store):
    """Vérifie le filtrage par catégorie."""
    # Ajouter un souvenir d'une autre catégorie
    store.add_memory(
        category="preference",
        content="Je préfère les systèmes simples.",
        importance_score=0.7,
        ttl_days=30,
    )

    results = searcher.search(query="systèmes", limit=10, category="fact")
    assert all(r["category"] == "fact" for r in results)


def test_search_empty_query(searcher, sample_memories):
    """Vérifie qu'une requête vide renvoie une liste vide."""
    assert searcher.search(query="", limit=5) == []


def test_search_no_memories(searcher, store):
    """Vérifie le comportement quand il n'y a aucun souvenir."""
    # Base vide : nouveau store avec DB temporaire
    empty_db = Database(":memory:")
    Base.metadata.create_all(empty_db.engine)
    empty_store = MemoryStore(db=empty_db, use_memory_rank=True)
    empty_searcher = SemanticSearcher(memory_store=empty_store)

    results = empty_searcher.search(query="test", limit=5)
    assert results == []




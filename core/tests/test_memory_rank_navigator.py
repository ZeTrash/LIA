"""Tests pour MemoryRankNavigator."""

import pytest
from datetime import datetime, timedelta, UTC

from memory_service.db import Database
from memory_service.models import Base, SouvenirModel, TraitModel, MemoryLinkModel
from memory_service.store import MemoryStore
from core.memory_rank_navigator import MemoryRankNavigator


@pytest.fixture
def test_db(tmp_path):
    """Crée une base de données temporaire pour les tests."""
    db_path = tmp_path / "test_memory_nav.db"
    db = Database(str(db_path))
    Base.metadata.create_all(db.engine)
    yield db
    db.close()


@pytest.fixture
def store(test_db):
    """Crée un MemoryStore pour les tests."""
    return MemoryStore(db=test_db, use_memory_rank=True)


@pytest.fixture
def navigator(store):
    """Crée un MemoryRankNavigator pour les tests."""
    return MemoryRankNavigator(memory_store=store)


@pytest.fixture
def sample_memories(store):
    """Crée des souvenirs de test avec différents MemoryRank."""
    session = store.db.get_session()
    try:
        now = datetime.now(UTC)
        ttl = now + timedelta(days=30)

        data = [
            ("Je suis LIA, un assistant IA", 0.85),
            ("Mon objectif est d'aider les utilisateurs", 0.72),
            ("J'utilise Python pour le développement", 0.65),
        ]

        ids = []
        for content, rank in data:
            mem = SouvenirModel(
                memory_id=f"mem_{len(ids)}",
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
            ids.append(mem.memory_id)

        session.commit()
        return ids
    finally:
        session.close()


def test_get_top_memories_basic(navigator, sample_memories):
    """Vérifie que get_top_memories renvoie des souvenirs triés par MemoryRank."""
    results = navigator.get_top_memories(limit=2)
    assert len(results) == 2
    assert results[0]["memory_rank_score"] >= results[1]["memory_rank_score"]
    assert results[0]["memory_rank_score"] == 0.85


def test_get_connected_memories(navigator, store, sample_memories):
    """Vérifie la récupération des souvenirs liés."""
    session = store.db.get_session()
    try:
        now = datetime.now(UTC)
        # Créer un lien entre le premier et le second
        link = MemoryLinkModel(
            link_id="link_1",
            source_memory_id=sample_memories[0],
            target_memory_id=sample_memories[1],
            weight=0.9,
            link_type="cooccurrence",
            link_metadata=None,
            created_at=now,
            updated_at=now,
        )
        session.add(link)
        session.commit()
    finally:
        session.close()

    results = navigator.get_connected_memories(memory_id=sample_memories[0], limit=10)
    assert len(results) == 1
    assert results[0]["memory_id"] == sample_memories[1]
    assert results[0]["link_weight"] == 0.9


def test_get_top_traits(navigator, store):
    """Vérifie la récupération des traits les plus importants."""
    # Créer quelques traits
    store.add_trait(trait_type="persona", label="Style de Réponse", value="pro", weight=5.0)
    store.add_trait(trait_type="persona", label="Relation", value="bienveillant", weight=4.0)

    results = navigator.get_top_traits(limit=2, trait_type="persona")
    assert len(results) == 2
    assert results[0]["weight"] >= results[1]["weight"]


def test_get_identity_phrases(navigator, store):
    """Vérifie la récupération des phrases d'identité."""
    now = datetime.now(UTC)
    ttl = now + timedelta(days=30)
    session = store.db.get_session()
    try:
        mem1 = SouvenirModel(
            memory_id="id_1",
            category="fact",
            content="Je suis LIA, mon identité est d'aider.",
            tags="identité",
            importance_score=0.7,
            recency_score=1.0,
            emotion_score=0.0,
            memory_rank_score=0.9,
            frequency=1,
            ttl=ttl,
            created_at=now,
            updated_at=now,
        )
        mem2 = SouvenirModel(
            memory_id="id_2",
            category="fact",
            content="Un autre souvenir non lié à l'identité.",
            tags=None,
            importance_score=0.5,
            recency_score=0.5,
            emotion_score=0.0,
            memory_rank_score=0.3,
            frequency=1,
            ttl=ttl,
            created_at=now,
            updated_at=now,
        )
        session.add(mem1)
        session.add(mem2)
        session.commit()
    finally:
        session.close()

    results = navigator.get_identity_phrases(limit=5)
    assert len(results) >= 1
    contents = [r["content"] for r in results]
    assert any("identité" in c.lower() or "identity" in c.lower() for c in contents)




"""Tests pour le système MemoryRank."""

import pytest
import tempfile
import os
from datetime import datetime, UTC, timedelta
from pathlib import Path

from memory_service.models import Base, SouvenirModel, MemoryLinkModel
from memory_service.db import Database
from memory_service.memory_rank import MemoryRank
from memory_service.memory_rank_engine import MemoryRankEngine
from memory_service.store import MemoryStore
from memory_service.memory_rank_extensions import FractalMemoryRank, RLMemoryRank, MemoryLevel


@pytest.fixture
def temp_db():
    """Crée une base de données temporaire pour les tests."""
    # Créer un fichier temporaire
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Créer la base de données
    db = Database(db_path=path)
    Base.metadata.create_all(db.engine)
    
    yield db
    
    # Nettoyer
    db.close()
    os.unlink(path)


@pytest.fixture
def sample_memories(temp_db):
    """Crée des souvenirs de test."""
    session = temp_db.get_session()
    try:
        memories = []
        for i in range(5):
            memory = SouvenirModel(
                memory_id=f"mem_{i}",
                category="fact",
                content=f"Contenu du souvenir {i}",
                tags=f"tag{i}",
                importance_score=0.5,
                recency_score=0.5,
                ttl=datetime.now(UTC) + timedelta(days=30),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            session.add(memory)
            memories.append(memory)
        
        session.commit()
        return memories
    finally:
        session.close()


def test_memory_rank_basic(temp_db, sample_memories):
    """Test basique de l'algorithme MemoryRank."""
    memory_rank = MemoryRank()
    
    # Créer des liens simples
    memory_ids = [m.memory_id for m in sample_memories]
    links = [
        (memory_ids[0], memory_ids[1], 1.0),  # mem_0 -> mem_1
        (memory_ids[1], memory_ids[2], 1.0),  # mem_1 -> mem_2
        (memory_ids[2], memory_ids[0], 1.0),  # mem_2 -> mem_0 (cycle)
    ]
    
    # Calculer les rangs
    ranks = memory_rank.compute_ranks(memory_ids, links)
    
    # Vérifier que tous les souvenirs ont un score
    assert len(ranks) == len(memory_ids)
    assert all(0.0 <= score <= 1.0 for score in ranks.values())
    
    # Vérifier que les souvenirs connectés ont des scores non-nuls
    assert ranks[memory_ids[0]] > 0
    assert ranks[memory_ids[1]] > 0
    assert ranks[memory_ids[2]] > 0


def test_memory_rank_engine_add_link(temp_db, sample_memories):
    """Test de l'ajout de liens via MemoryRankEngine."""
    engine = MemoryRankEngine(db=temp_db)
    
    # Ajouter un lien
    link_id = engine.add_link(
        source_memory_id=sample_memories[0].memory_id,
        target_memory_id=sample_memories[1].memory_id,
        weight=1.5,
        link_type="cooccurrence"
    )
    
    assert link_id is not None
    
    # Vérifier que le lien existe
    session = temp_db.get_session()
    try:
        link = session.query(MemoryLinkModel).filter(
            MemoryLinkModel.link_id == link_id
        ).first()
        assert link is not None
        assert link.weight == 1.5
        assert link.link_type == "cooccurrence"
    finally:
        session.close()


def test_memory_rank_engine_compute_ranks(temp_db, sample_memories):
    """Test du calcul et de la mise à jour des scores MemoryRank."""
    engine = MemoryRankEngine(db=temp_db)
    
    # Créer quelques liens
    engine.add_link(sample_memories[0].memory_id, sample_memories[1].memory_id, 1.0, "cooccurrence")
    engine.add_link(sample_memories[1].memory_id, sample_memories[2].memory_id, 1.0, "cooccurrence")
    engine.add_link(sample_memories[2].memory_id, sample_memories[0].memory_id, 1.0, "cooccurrence")
    
    # Calculer les rangs
    ranks = engine.compute_and_update_ranks()
    
    # Vérifier que les scores ont été calculés
    assert len(ranks) > 0
    
    # Vérifier que les scores ont été mis à jour dans la base
    session = temp_db.get_session()
    try:
        for memory_id, expected_rank in ranks.items():
            memory = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == memory_id
            ).first()
            assert memory is not None
            assert abs(memory.memory_rank_score - expected_rank) < 1e-6
    finally:
        session.close()


def test_memory_store_with_memory_rank(temp_db, sample_memories):
    """Test de l'intégration MemoryRank dans MemoryStore."""
    store = MemoryStore(db=temp_db, use_memory_rank=True)
    
    # Créer quelques liens
    store.add_memory_link(
        sample_memories[0].memory_id,
        sample_memories[1].memory_id,
        weight=1.0,
        link_type="cooccurrence"
    )
    
    # Mettre à jour les rangs
    ranks = store.update_memory_ranks()
    assert len(ranks) > 0
    
    # Récupérer le contexte (devrait utiliser MemoryRank)
    context = store.get_context(limit_memories=5)
    
    # Vérifier que les souvenirs ont des scores MemoryRank
    assert "memories" in context
    for memory in context["memories"]:
        assert "memory_rank_score" in memory
        assert isinstance(memory["memory_rank_score"], float)


def test_memory_rank_temporal_decay(temp_db, sample_memories):
    """Test de la décroissance temporelle."""
    memory_rank = MemoryRank()
    
    memory_ids = [m.memory_id for m in sample_memories]
    links = [
        (memory_ids[0], memory_ids[1], 1.0),
    ]
    
    # Créer des âges différents pour les souvenirs
    memory_ages = {
        memory_ids[0]: 0.0,  # Nouveau
        memory_ids[1]: 10.0,  # 10 jours
        memory_ids[2]: 30.0,  # 30 jours
    }
    
    # Calculer avec décroissance temporelle
    ranks = memory_rank.compute_ranks_with_temporal_decay(
        memory_ids, links, memory_ages, decay_factor=0.01
    )
    
    # Vérifier que les souvenirs plus anciens ont des scores plus faibles
    assert ranks[memory_ids[0]] > ranks[memory_ids[1]]
    assert ranks[memory_ids[1]] > ranks[memory_ids[2]]


def test_hybrid_score():
    """Test du calcul de score hybride."""
    memory_rank = MemoryRank()
    
    # Test avec MemoryRank seul
    score = memory_rank.compute_hybrid_score(
        memory_rank=0.5,
        alpha=1.0
    )
    assert score == 0.5
    
    # Test avec MemoryRank + Reward
    score = memory_rank.compute_hybrid_score(
        memory_rank=0.5,
        reward_score=0.8,
        alpha=0.5,
        beta=0.5
    )
    assert 0.5 <= score <= 0.8
    
    # Test avec les trois composantes
    score = memory_rank.compute_hybrid_score(
        memory_rank=0.5,
        reward_score=0.8,
        similarity_score=0.3,
        alpha=0.5,
        beta=0.3,
        gamma=0.2
    )
    assert 0.0 <= score <= 1.0


def test_fractal_memory_rank(temp_db, sample_memories):
    """Test de la hiérarchie fractale."""
    fractal_rank = FractalMemoryRank(db=temp_db)
    
    # Calculer les rangs pour un niveau
    ranks = fractal_rank.compute_hierarchical_ranks(MemoryLevel.EVENT)
    
    # Vérifier que les rangs sont calculés (peut être vide si aucun souvenir n'est identifié comme EVENT)
    assert isinstance(ranks, dict)


def test_rl_memory_rank(temp_db, sample_memories):
    """Test de l'intégration RL."""
    rl_rank = RLMemoryRank(db=temp_db)
    
    # Mettre à jour un souvenir avec une récompense
    success = rl_rank.update_memory_with_reward(
        sample_memories[0].memory_id,
        reward=0.8
    )
    assert success
    
    # Vérifier que l'importance a été mise à jour
    session = temp_db.get_session()
    try:
        memory = session.query(SouvenirModel).filter(
            SouvenirModel.memory_id == sample_memories[0].memory_id
        ).first()
        assert memory.importance_score > 0
    finally:
        session.close()


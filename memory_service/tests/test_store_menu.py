"""Tests pour les nouvelles méthodes du MemoryStore pour le menu optimal."""

import pytest
from datetime import datetime, timedelta, UTC
import uuid
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au PYTHONPATH pour les imports memory_service
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory_service.store import MemoryStore
from memory_service.db import Database
from memory_service.models import Base, SouvenirModel, TraitModel, MemoryLinkModel


@pytest.fixture
def test_db(tmp_path):
    """Crée une base de données temporaire pour les tests."""
    db_path = tmp_path / "test_memory.db"
    db = Database(str(db_path))
    Base.metadata.create_all(db.engine)
    yield db
    db.close()


@pytest.fixture
def store(test_db):
    """Crée un MemoryStore pour les tests."""
    return MemoryStore(db=test_db, use_memory_rank=True)


@pytest.fixture
def sample_memories(store):
    """Crée des souvenirs de test avec différents MemoryRank."""
    memories = []
    
    # Créer des souvenirs avec différents scores MemoryRank
    for i, (content, rank) in enumerate([
        ("Je suis LIA, un assistant IA", 0.85),
        ("Mon objectif est d'aider les utilisateurs", 0.72),
        ("J'utilise Python pour le développement", 0.65),
        ("J'aime travailler sur des projets d'IA", 0.58),
        ("Je préfère les solutions simples", 0.45),
    ]):
        memory_id = store.add_memory(
            category="fact",
            content=content,
            importance_score=0.7,
            ttl_days=30
        )
        # Mettre à jour le MemoryRank directement dans la DB
        session = store.db.get_session()
        try:
            memory = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == memory_id
            ).first()
            memory.memory_rank_score = rank
            session.commit()
        finally:
            session.close()
        
        memories.append(memory_id)
    
    return memories


@pytest.fixture
def sample_traits(store):
    """Crée des traits de test avec différents poids."""
    traits = []
    
    for label, weight in [
        ("Style de Réponse", 5.0),
        ("Relation à l'utilisateur", 4.5),
        ("Capacités Cognitives", 4.0),
        ("Style de Communication", 3.5),
        ("Approche", 3.0),
    ]:
        trait_id = store.add_trait(
            trait_type="persona",
            label=label,
            value=f"Valeur pour {label}",
            weight=weight
        )
        traits.append(trait_id)
    
    return traits


class TestGetTopMemoriesByRank:
    """Tests pour get_top_memories_by_rank()."""
    
    def test_get_top_memories_by_rank_basic(self, store, sample_memories):
        """Test récupération des top souvenirs par MemoryRank."""
        results = store.get_top_memories_by_rank(limit=3)
        
        assert len(results) == 3
        # Vérifier que les résultats sont triés par MemoryRank décroissant
        assert results[0]['memory_rank_score'] >= results[1]['memory_rank_score']
        assert results[1]['memory_rank_score'] >= results[2]['memory_rank_score']
        # Vérifier que le premier a le score le plus élevé
        assert results[0]['memory_rank_score'] == 0.85
    
    def test_get_top_memories_by_rank_with_category(self, store, sample_memories):
        """Test filtrage par catégorie."""
        # Ajouter un souvenir dans une autre catégorie
        other_id = store.add_memory(
            category="preference",
            content="Je préfère Python",
            importance_score=0.8,
            ttl_days=30
        )
        
        # Mettre à jour MemoryRank
        session = store.db.get_session()
        try:
            memory = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == other_id
            ).first()
            memory.memory_rank_score = 0.90
            session.commit()
        finally:
            session.close()
        
        # Récupérer seulement les "fact"
        results = store.get_top_memories_by_rank(limit=10, category="fact")
        
        assert all(r['category'] == 'fact' for r in results)
        assert len(results) == 5  # Tous les souvenirs de test sont "fact"
    
    def test_get_top_memories_by_rank_with_min_rank(self, store, sample_memories):
        """Test filtrage par score MemoryRank minimum."""
        results = store.get_top_memories_by_rank(limit=10, min_rank=0.7)
        
        assert len(results) == 2  # Seulement ceux avec rank >= 0.7
        assert all(r['memory_rank_score'] >= 0.7 for r in results)
    
    def test_get_top_memories_by_rank_empty(self, store):
        """Test avec aucune mémoire."""
        results = store.get_top_memories_by_rank(limit=10)
        assert results == []


class TestGetMemoryLinks:
    """Tests pour get_memory_links()."""
    
    def test_get_memory_links_basic(self, store, sample_memories):
        """Test récupération des souvenirs liés."""
        # Créer des liens entre souvenirs
        source_id = sample_memories[0]
        target_ids = sample_memories[1:3]
        
        for i, target_id in enumerate(target_ids):
            store.add_memory_link(
                source_memory_id=source_id,
                target_memory_id=target_id,
                weight=0.9 - i * 0.1,
                link_type="cooccurrence"
            )
        
        # Récupérer les liens
        results = store.get_memory_links(source_id, limit=10)
        
        assert len(results) == 2
        # Vérifier que les résultats incluent les informations de lien
        assert 'link_weight' in results[0]
        assert 'link_type' in results[0]
        # Vérifier que les résultats sont triés par poids de lien
        assert results[0]['link_weight'] >= results[1]['link_weight']
    
    def test_get_memory_links_empty(self, store, sample_memories):
        """Test avec aucun lien."""
        source_id = sample_memories[0]
        results = store.get_memory_links(source_id, limit=10)
        assert results == []
    
    def test_get_memory_links_with_limit(self, store, sample_memories):
        """Test avec limite."""
        source_id = sample_memories[0]
        
        # Créer plusieurs liens
        for target_id in sample_memories[1:]:
            store.add_memory_link(
                source_memory_id=source_id,
                target_memory_id=target_id,
                weight=0.8,
                link_type="cooccurrence"
            )
        
        results = store.get_memory_links(source_id, limit=2)
        assert len(results) <= 2


class TestGetTopTraitsByRank:
    """Tests pour get_top_traits_by_rank()."""
    
    def test_get_top_traits_by_rank_basic(self, store, sample_traits):
        """Test récupération des top traits par poids."""
        results = store.get_top_traits_by_rank(limit=3)
        
        assert len(results) == 3
        # Vérifier que les résultats sont triés par poids décroissant
        assert results[0]['weight'] >= results[1]['weight']
        assert results[1]['weight'] >= results[2]['weight']
        # Vérifier que le premier a le poids le plus élevé
        assert results[0]['weight'] == 5.0
    
    def test_get_top_traits_by_rank_with_type(self, store, sample_traits):
        """Test filtrage par type de trait."""
        # Ajouter un trait d'un autre type
        other_id = store.add_trait(
            trait_type="skill",
            label="Compétence Technique",
            value="Python",
            weight=6.0
        )
        
        # Récupérer seulement les "persona"
        results = store.get_top_traits_by_rank(limit=10, trait_type="persona")
        
        assert all(r['type'] == 'persona' for r in results)
        assert len(results) == 5  # Tous les traits de test sont "persona"
    
    def test_get_top_traits_by_rank_empty(self, store):
        """Test avec aucun trait."""
        results = store.get_top_traits_by_rank(limit=10)
        assert results == []


class TestSearchMemoriesSemantic:
    """Tests pour search_memories_semantic()."""
    
    def test_search_memories_semantic_basic(self, store, sample_memories):
        """Test recherche sémantique basique."""
        results = store.search_memories_semantic(
            query="assistant IA",
            limit=5
        )
        
        assert len(results) > 0
        # Vérifier que les résultats incluent les scores de recherche
        assert 'search_score' in results[0]
        assert 'search_similarity' in results[0]
        # Vérifier que les résultats sont triés par score décroissant
        assert results[0]['search_score'] >= results[-1]['search_score']
    
    def test_search_memories_semantic_with_category(self, store, sample_memories):
        """Test recherche sémantique avec filtre de catégorie."""
        # Ajouter un souvenir dans une autre catégorie
        other_id = store.add_memory(
            category="preference",
            content="J'aime les assistants IA",
            importance_score=0.7,
            ttl_days=30
        )
        
        results = store.search_memories_semantic(
            query="assistant",
            limit=10,
            category="fact"
        )
        
        assert all(r['category'] == 'fact' for r in results)
    
    def test_search_memories_semantic_weights(self, store, sample_memories):
        """Test avec différents poids alpha/beta."""
        # Recherche avec plus de poids sur MemoryRank
        results_rank = store.search_memories_semantic(
            query="assistant",
            limit=5,
            alpha=0.3,
            beta=0.7
        )
        
        # Recherche avec plus de poids sur similarité
        results_sim = store.search_memories_semantic(
            query="assistant",
            limit=5,
            alpha=0.8,
            beta=0.2
        )
        
        # Les résultats peuvent être différents selon les poids
        assert len(results_rank) > 0
        assert len(results_sim) > 0
    
    def test_search_memories_semantic_empty_query(self, store, sample_memories):
        """Test avec requête vide."""
        results = store.search_memories_semantic(query="", limit=10)
        assert results == []
    
    def test_search_memories_semantic_no_results(self, store):
        """Test sans souvenirs."""
        results = store.search_memories_semantic(query="test", limit=10)
        assert results == []


class TestHelperMethods:
    """Tests pour les méthodes helper."""
    
    def test_memory_to_dict(self, store):
        """Test conversion SouvenirModel en dict."""
        memory_id = store.add_memory(
            category="fact",
            content="Test content",
            importance_score=0.7,
            ttl_days=30
        )
        
        session = store.db.get_session()
        try:
            memory = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == memory_id
            ).first()
            
            result = store._memory_to_dict(memory)
            
            assert result['memory_id'] == memory_id
            assert result['category'] == 'fact'
            assert result['content'] == 'Test content'
            assert 'memory_rank_score' in result
            assert 'created_at' in result
        finally:
            session.close()
    
    def test_trait_to_dict(self, store):
        """Test conversion TraitModel en dict."""
        trait_id = store.add_trait(
            trait_type="persona",
            label="Test Trait",
            value="Test Value",
            weight=5.0
        )
        
        session = store.db.get_session()
        try:
            trait = session.query(TraitModel).filter(
                TraitModel.trait_id == trait_id
            ).first()
            
            result = store._trait_to_dict(trait)
            
            assert result['trait_id'] == trait_id
            assert result['type'] == 'persona'
            assert result['label'] == 'Test Trait'
            assert result['weight'] == 5.0
            assert 'last_update' in result
        finally:
            session.close()


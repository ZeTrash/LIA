"""Tests pour les objectifs personnels (Étape 2.6)."""

import sys
from pathlib import Path
from datetime import datetime, UTC, timedelta

import pytest

# Ajouter le répertoire src au PYTHONPATH
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_service.schemas import PersonalGoal, PersonalGoalCreate, PersonalGoalUpdate
from memory_service.store import MemoryStore
from memory_service.config import Settings
from memory_service.db import create_session_factory


@pytest.fixture
def settings():
    """Settings de test."""
    return Settings(database_url="sqlite:///:memory:")


@pytest.fixture
def store(settings):
    """MemoryStore de test."""
    session_factory = create_session_factory(settings)
    return MemoryStore(settings, session_factory)


def test_personal_goal_create_schema():
    """Test du schéma PersonalGoalCreate."""
    goal_data = PersonalGoalCreate(
        goal_type="research",
        description="Explorer la philosophie",
        priority=0.8,
        frequency="weekly",
    )
    
    assert goal_data.goal_type == "research"
    assert goal_data.description == "Explorer la philosophie"
    assert goal_data.priority == 0.8
    assert goal_data.frequency == "weekly"


def test_personal_goal_schema():
    """Test du schéma PersonalGoal."""
    now = datetime.now(UTC)
    goal = PersonalGoal(
        goal_id="goal-test-1",
        goal_type="research",
        description="Test",
        priority=0.5,
        status="active",
        frequency="daily",
        created_at=now,
    )
    
    assert goal.goal_id == "goal-test-1"
    assert goal.status == "active"


def test_create_personal_goal(store):
    """Test de création d'objectif."""
    goal_data = PersonalGoalCreate(
        goal_type="research",
        description="Test research",
        priority=0.7,
        frequency="daily",
    )
    
    goal = store.create_personal_goal(goal_data)
    
    assert goal.goal_id is not None
    assert goal.goal_type == "research"
    assert goal.description == "Test research"
    assert goal.status == "active"
    assert goal.priority == 0.7


def test_get_personal_goals(store):
    """Test de récupération des objectifs."""
    # Créer quelques objectifs
    goal1 = store.create_personal_goal(PersonalGoalCreate(
        goal_type="research",
        description="Research 1",
        frequency="daily",
    ))
    goal2 = store.create_personal_goal(PersonalGoalCreate(
        goal_type="hobby",
        description="Hobby 1",
        frequency="weekly",
    ))
    
    # Récupérer tous
    all_goals = store.get_personal_goals()
    assert len(all_goals) >= 2
    
    # Filtrer par type
    research_goals = store.get_personal_goals(goal_type="research")
    assert len(research_goals) >= 1
    assert all(g.goal_type == "research" for g in research_goals)
    
    # Filtrer par statut
    active_goals = store.get_personal_goals(status="active")
    assert len(active_goals) >= 2


def test_get_personal_goal(store):
    """Test de récupération d'un objectif par ID."""
    goal_data = PersonalGoalCreate(
        goal_type="task",
        description="Test task",
        frequency="once",
    )
    
    created = store.create_personal_goal(goal_data)
    retrieved = store.get_personal_goal(created.goal_id)
    
    assert retrieved is not None
    assert retrieved.goal_id == created.goal_id
    assert retrieved.description == "Test task"


def test_update_personal_goal(store):
    """Test de mise à jour d'objectif."""
    goal = store.create_personal_goal(PersonalGoalCreate(
        goal_type="research",
        description="Original",
        priority=0.5,
        frequency="daily",
    ))
    
    update_data = PersonalGoalUpdate(
        description="Updated",
        priority=0.9,
        status="paused",
    )
    
    updated = store.update_personal_goal(goal.goal_id, update_data)
    
    assert updated is not None
    assert updated.description == "Updated"
    assert updated.priority == 0.9
    assert updated.status == "paused"


def test_delete_personal_goal(store):
    """Test de suppression d'objectif."""
    goal = store.create_personal_goal(PersonalGoalCreate(
        goal_type="research",
        description="To delete",
        frequency="once",
    ))
    
    deleted = store.delete_personal_goal(goal.goal_id)
    assert deleted is True
    
    # Vérifier qu'il n'existe plus
    retrieved = store.get_personal_goal(goal.goal_id)
    assert retrieved is None


def test_get_goals_to_trigger(store):
    """Test de récupération des objectifs à déclencher."""
    now = datetime.now(UTC)
    past_time = now - timedelta(hours=1)
    future_time = now + timedelta(hours=1)
    
    # Créer objectif avec next_trigger_at dans le passé
    goal1 = store.create_personal_goal(PersonalGoalCreate(
        goal_type="research",
        description="Past trigger",
        frequency="daily",
    ))
    # Mettre à jour pour avoir next_trigger_at dans le passé
    store.update_personal_goal(goal1.goal_id, PersonalGoalUpdate(
        next_trigger_at=past_time
    ))
    
    # Créer objectif avec next_trigger_at dans le futur
    goal2 = store.create_personal_goal(PersonalGoalCreate(
        goal_type="research",
        description="Future trigger",
        frequency="daily",
    ))
    store.update_personal_goal(goal2.goal_id, PersonalGoalUpdate(
        next_trigger_at=future_time
    ))
    
    # Récupérer ceux à déclencher
    to_trigger = store.get_goals_to_trigger()
    
    # Vérifier que goal1 est dans la liste
    goal_ids = [g.goal_id for g in to_trigger]
    assert goal1.goal_id in goal_ids
    assert goal2.goal_id not in goal_ids

"""Tests pour MenuBuilder (hints MemoryRank + N dynamiques + recommandation pattern)."""

import pytest
from datetime import datetime, timedelta, UTC

from memory_service.db import Database
from memory_service.models import Base, SouvenirModel
from memory_service.store import MemoryStore

from core.menu_builder import MenuBuilder
from core.cognitive_models import ActionType


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_menu_builder.db"
    db = Database(str(db_path))
    Base.metadata.create_all(db.engine)
    yield db
    db.close()


@pytest.fixture
def store(test_db):
    return MemoryStore(db=test_db, use_memory_rank=True)


@pytest.fixture
def builder(store):
    return MenuBuilder(memory_store=store, pattern_learner=None, config={"default_memory_limit": 5})


@pytest.fixture
def seed_data(store):
    """Ajoute quelques souvenirs/traits pour générer des previews/hints."""
    # Traits via store.add_trait
    store.add_trait("persona", "Style de Réponse", "pro", weight=5.0)
    store.add_trait("persona", "Relation à l'utilisateur", "bienveillant", weight=4.0)

    # Souvenirs avec rank (mise à jour directe pour contrôle)
    ids = []
    for content, rank, tags in [
        ("Je suis LIA. Identité: aider.", 0.9, ["identité"]),
        ("Souvenir important sur Python.", 0.8, ["python"]),
        ("Souvenir secondaire.", 0.2, []),
    ]:
        mid = store.add_memory(category="fact", content=content, tags=tags, importance_score=0.7, ttl_days=30)
        ids.append(mid)
        session = store.db.get_session()
        try:
            m = session.query(SouvenirModel).filter(SouvenirModel.memory_id == mid).first()
            m.memory_rank_score = rank
            session.commit()
        finally:
            session.close()
    return ids


def _find_action(menu, action_type: ActionType):
    for a in menu:
        if a.type == action_type:
            return a
    return None


def test_general_menu_includes_hints_and_dynamic_limits(builder, seed_data):
    execution_results = {"_menu_state": "general", "_theme_pattern": "mémoire"}
    menu = builder.build_general_menu("Parle-moi de mémoire et Python", execution_results, session_id="s1")

    a_traits = _find_action(menu, ActionType.CONSULT_TRAITS)
    a_mem = _find_action(menu, ActionType.CONSULT_MEMORY)
    a_search = _find_action(menu, ActionType.SEARCH_MEMORY)

    assert a_traits is not None
    assert a_mem is not None
    assert a_search is not None

    # Hints présents
    assert isinstance(a_traits.parameters.get("_preview"), list)
    assert isinstance(a_mem.parameters.get("_preview"), list)
    assert isinstance(a_search.parameters.get("_preview"), list)

    # N dynamiques bornés
    assert 5 <= int(a_traits.parameters.get("limit")) <= 20
    assert 3 <= int(a_mem.parameters.get("limit")) <= 10
    assert int(a_search.parameters.get("limit")) >= 10


def test_base_menu_contains_density_hint(builder, seed_data):
    execution_results = {"_menu_state": "base", "_theme_pattern": "identité"}
    menu = builder.build_base_menu("Qui es-tu ?", execution_results, session_id="s1")

    nav = _find_action(menu, ActionType.NAVIGATE_GENERAL)
    assert nav is not None
    # Hint optionnel mais si présent doit être str
    if "_hint" in nav.parameters:
        assert isinstance(nav.parameters["_hint"], str)



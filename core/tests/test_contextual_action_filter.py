"""Tests pour ContextualActionFilter."""

import pytest

from core.contextual_action_filter import ContextualActionFilter
from core.cognitive_models import Action
from core.cognitive_models import ActionType


@pytest.fixture
def action_filter():
    return ContextualActionFilter()


def _make_action(action_type: ActionType) -> Action:
    return Action(type=action_type, parameters={}, priority=1, required=False)


def test_filter_actions_keeps_all_by_default(action_filter):
    """Par défaut, le filtre est très conservateur et garde toutes les actions."""
    actions = [
        _make_action(ActionType.NAVIGATE_GENERAL),
        _make_action(ActionType.CONSULT_IDENTITY),
        _make_action(ActionType.RESPOND),
    ]
    execution_results = {}

    filtered = action_filter.filter_actions(actions, execution_results, user_request="test")

    assert len(filtered) == len(actions)
    assert any(a.type == ActionType.RESPOND for a in filtered)


def test_filter_actions_avoids_immediate_same_navigation(action_filter):
    """Évite de reproposer immédiatement la même action de navigation."""
    actions = [
        _make_action(ActionType.NAVIGATE_GENERAL),
        _make_action(ActionType.RESPOND),
    ]
    execution_results = {"_last_action_type": ActionType.NAVIGATE_GENERAL.value}

    filtered = action_filter.filter_actions(actions, execution_results, user_request="test")

    # NAVIGATE_GENERAL devrait être filtrée, RESPOND conservée
    assert any(a.type == ActionType.RESPOND for a in filtered)
    assert all(a.type != ActionType.NAVIGATE_GENERAL for a in filtered)


def test_filter_actions_always_keep_respond(action_filter):
    """RESPOND est toujours considéré comme pertinent."""
    actions = [
        _make_action(ActionType.RESPOND),
    ]
    execution_results = {"_last_action_type": ActionType.RESPOND.value}

    filtered = action_filter.filter_actions(actions, execution_results, user_request="test")

    assert len(filtered) == 1
    assert filtered[0].type == ActionType.RESPOND




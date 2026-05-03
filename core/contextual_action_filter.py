"""Filtrage contextuel des actions du menu cognitif.

Responsabilité :
- éviter certaines répétitions inutiles,
- donner un point d'extension pour plus tard (priorisation par contexte),
- rester très conservateur au début (ne pas supprimer des actions critiques).
"""

from __future__ import annotations

from typing import Any, Dict, List

from .cognitive_models import Action, ActionType


class ContextualActionFilter:
    """Filtre les actions selon le contexte et l'historique."""

    def filter_actions(
        self,
        actions: List[Action],
        execution_results: Dict[str, Any],
        user_request: str,
    ) -> List[Action]:
        """Filtre les actions.

        Stratégie de base (conservatrice) :
        - ne jamais retirer RESPOND,
        - éviter de reproposer certaines actions de navigation immédiates
          si elles viennent d'être exécutées (ex: NAVIGATE_GENERAL),
        - pour le reste, laisser passer.
        """
        if not actions:
            return []

        last_action_type = execution_results.get("_last_action_type")

        filtered: List[Action] = []
        for a in actions:
            if not self._is_action_relevant(a, user_request, execution_results):
                continue

            # Exemple simple : ne pas reproposer immédiatement la même navigation
            if (
                last_action_type
                and a.type.value == last_action_type
                and a.type in (ActionType.NAVIGATE_GENERAL, ActionType.NAVIGATE_BASE)
            ):
                # On skippe la navigation identique juste après
                continue

            filtered.append(a)

        # Toujours garantir au moins une action
        return filtered or actions

    def _is_action_relevant(
        self,
        action: Action,
        user_request: str,
        execution_results: Dict[str, Any],
    ) -> bool:
        """Détermine si une action est pertinente au contexte.

        Implémentation minimale :
        - toujours considérer RESPOND comme pertinent,
        - pour les autres, on retourne True (point d'extension futur).
        """
        # RESPOND est toujours pertinent
        if action.type.value == "RESPOND":
            return True

        # À ce stade, on ne filtre rien d'autre.
        # Plus tard, on pourra utiliser :
        # - des heuristiques sur user_request,
        # - l'historique dans execution_results,
        # - les patterns et MemoryRank.
        return True



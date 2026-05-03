"""CognitiveSafeguards: garde-fous pour éviter l'explosion de complexité (Phase 5).

Ce module implémente des mécanismes de protection contre :
- Boucles cognitives infinies
- Dépenses excessives de tokens/temps
- Accès mémoire trop fréquents
- Profondeur de décision excessive
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from collections import deque

from .cognitive_models import ActionPlan, Action, ActionType

logger = logging.getLogger(__name__)


@dataclass
class SafeguardConfig:
    """Configuration des garde-fous."""

    max_decision_depth: int = 3  # Profondeur maximale de décision
    max_reflection_tokens: int = 500  # Budget de tokens pour réflexion
    max_reflection_time: float = 2.0  # Budget de temps (secondes)
    max_memory_access_cost: float = 100.0  # Coût maximum d'accès mémoire
    max_actions_per_plan: int = 10  # Nombre maximum d'actions par plan
    enable_loop_detection: bool = True  # Détecter les boucles cognitives
    max_loop_iterations: int = 3  # Nombre maximum d'itérations dans une boucle


@dataclass
class ReflectionBudget:
    """Budget de réflexion pour une session."""

    tokens_used: int = 0
    time_used: float = 0.0
    memory_cost: float = 0.0
    depth: int = 0
    action_count: int = 0
    visited_states: Set[str] = field(default_factory=set)
    recent_plans: deque = field(default_factory=lambda: deque(maxlen=5))


class CognitiveSafeguards:
    """Garde-fous pour le système cognitif."""

    def __init__(self, config: Optional[SafeguardConfig] = None):
        """
        Initialise les garde-fous.

        Args:
            config: Configuration des garde-fous
        """
        self.config = config or SafeguardConfig()
        self.budgets: Dict[str, ReflectionBudget] = {}  # Par session_id

        logger.info("CognitiveSafeguards initialisé")

    def get_budget(self, session_id: str) -> ReflectionBudget:
        """Récupère ou crée le budget pour une session."""
        if session_id not in self.budgets:
            self.budgets[session_id] = ReflectionBudget()
        return self.budgets[session_id]

    def check_decision_depth(self, session_id: str, current_depth: int) -> bool:
        """
        Vérifie si la profondeur de décision est acceptable.

        Returns:
            True si acceptable, False si limite dépassée
        """
        if current_depth > self.config.max_decision_depth:
            logger.warning(
                f"⚠️  Profondeur de décision dépassée: {current_depth} > {self.config.max_decision_depth}"
            )
            return False
        return True

    def check_reflection_budget(
        self, session_id: str, tokens: int = 0, time_elapsed: float = 0.0
    ) -> bool:
        """
        Vérifie si le budget de réflexion est respecté.

        Args:
            session_id: ID de session
            tokens: Tokens utilisés
            time_elapsed: Temps écoulé (secondes)

        Returns:
            True si budget OK, False si dépassé
        """
        budget = self.get_budget(session_id)

        # Vérifier budget tokens
        if budget.tokens_used + tokens > self.config.max_reflection_tokens:
            logger.warning(
                f"⚠️  Budget tokens dépassé: {budget.tokens_used + tokens} > {self.config.max_reflection_tokens}"
            )
            return False

        # Vérifier budget temps
        if budget.time_used + time_elapsed > self.config.max_reflection_time:
            logger.warning(
                f"⚠️  Budget temps dépassé: {budget.time_used + time_elapsed:.2f}s > {self.config.max_reflection_time}s"
            )
            return False

        return True

    def check_memory_cost(self, session_id: str, cost: float) -> bool:
        """
        Vérifie si le coût d'accès mémoire est acceptable.

        Args:
            session_id: ID de session
            cost: Coût de l'accès mémoire

        Returns:
            True si acceptable, False si limite dépassée
        """
        budget = self.get_budget(session_id)

        if budget.memory_cost + cost > self.config.max_memory_access_cost:
            logger.warning(
                f"⚠️  Coût mémoire dépassé: {budget.memory_cost + cost:.2f} > {self.config.max_memory_access_cost}"
            )
            return False

        return True

    def check_action_limit(self, plan: ActionPlan) -> bool:
        """
        Vérifie si le nombre d'actions dans le plan est acceptable.

        Args:
            plan: Plan d'actions à vérifier

        Returns:
            True si acceptable, False si limite dépassée
        """
        action_count = len(plan.actions)
        if action_count > self.config.max_actions_per_plan:
            logger.warning(
                f"⚠️  Nombre d'actions dépassé: {action_count} > {self.config.max_actions_per_plan}"
            )
            return False
        return True

    def detect_cognitive_loop(
        self, session_id: str, plan: ActionPlan, user_message: str = ""
    ) -> bool:
        """
        Détecte si un plan crée une boucle cognitive.

        Args:
            session_id: ID de session
            plan: Plan à vérifier
            user_message: Message utilisateur pour différencier les plans similaires

        Returns:
            True si boucle détectée, False sinon
        """
        if not self.config.enable_loop_detection:
            return False

        budget = self.get_budget(session_id)

        # Créer une signature du plan (séquence d'actions + hash du message)
        plan_signature = self._create_plan_signature(plan, user_message)
        logger.debug(f"🔍 [SAFEGUARDS] Vérification boucle cognitive: signature={plan_signature[:50]}...")

        # Vérifier si ce plan a déjà été utilisé récemment
        if plan_signature in budget.visited_states:
            # Compter combien de fois ce plan a été utilisé
            count = sum(1 for p in budget.recent_plans if p == plan_signature)
            logger.debug(f"  📊 [SAFEGUARDS] Plan déjà vu {count} fois (max: {self.config.max_loop_iterations})")
            if count >= self.config.max_loop_iterations:
                logger.warning(
                    f"⚠️  [SAFEGUARDS] Boucle cognitive détectée: plan répété {count} fois"
                )
                return True

        # Ajouter à l'historique
        budget.visited_states.add(plan_signature)
        budget.recent_plans.append(plan_signature)

        return False

    def _create_plan_signature(self, plan: ActionPlan, user_message: str = "") -> str:
        """Crée une signature unique pour un plan."""
        # Utiliser la séquence d'actions comme signature
        action_sequence = "->".join(
            [a.type.value for a in sorted(plan.actions, key=lambda a: a.priority)]
        )
        # Inclure un hash du message utilisateur pour différencier les plans similaires
        # mais pour des requêtes différentes
        if user_message:
            import hashlib
            msg_hash = hashlib.md5(user_message.lower().strip().encode()).hexdigest()[:8]
            return f"{action_sequence}|{msg_hash}"
        return action_sequence

    def validate_plan(
        self, session_id: str, plan: ActionPlan, current_depth: int = 0, user_message: str = ""
    ) -> tuple[bool, List[str]]:
        """
        Valide un plan complet contre tous les garde-fous.

        Args:
            session_id: ID de session
            plan: Plan à valider
            current_depth: Profondeur actuelle
            user_message: Message utilisateur pour différencier les plans similaires

        Returns:
            Tuple (is_valid, list_of_issues)
        """
        logger.debug(f"🛡️  [SAFEGUARDS] Validation du plan: {len(plan.actions)} actions, profondeur={current_depth}")
        issues: List[str] = []

        # Vérifier profondeur
        if not self.check_decision_depth(session_id, current_depth):
            issues.append(f"Profondeur excessive: {current_depth}")

        # Vérifier nombre d'actions
        if not self.check_action_limit(plan):
            issues.append(
                f"Trop d'actions: {len(plan.actions)} > {self.config.max_actions_per_plan}"
            )

        # Vérifier coût estimé
        if plan.estimated_cost > self.config.max_memory_access_cost:
            issues.append(
                f"Coût estimé trop élevé: {plan.estimated_cost:.2f} > {self.config.max_memory_access_cost}"
            )

        # Détecter boucles
        if self.detect_cognitive_loop(session_id, plan, user_message):
            issues.append("Boucle cognitive détectée")

        is_valid = len(issues) == 0
        if is_valid:
            logger.debug(f"  ✅ [SAFEGUARDS] Plan validé")
        else:
            logger.warning(f"  ⚠️  [SAFEGUARDS] Plan invalidé: {issues}")
        return is_valid, issues

    def record_reflection_usage(
        self,
        session_id: str,
        tokens: int = 0,
        time_elapsed: float = 0.0,
        memory_cost: float = 0.0,
    ) -> None:
        """
        Enregistre l'utilisation de ressources pour une session.

        Args:
            session_id: ID de session
            tokens: Tokens utilisés
            time_elapsed: Temps écoulé (secondes)
            memory_cost: Coût d'accès mémoire
        """
        budget = self.get_budget(session_id)
        budget.tokens_used += tokens
        budget.time_used += time_elapsed
        budget.memory_cost += memory_cost
        budget.depth += 1

    def reset_budget(self, session_id: str) -> None:
        """Réinitialise le budget pour une session."""
        if session_id in self.budgets:
            self.budgets[session_id] = ReflectionBudget()
            logger.debug(f"Budget réinitialisé pour session {session_id}")

    def get_budget_status(self, session_id: str) -> Dict[str, Any]:
        """
        Retourne le statut du budget pour une session.

        Returns:
            Dictionnaire avec les statistiques du budget
        """
        budget = self.get_budget(session_id)

        return {
            "tokens_used": budget.tokens_used,
            "tokens_remaining": max(0, self.config.max_reflection_tokens - budget.tokens_used),
            "time_used": budget.time_used,
            "time_remaining": max(0.0, self.config.max_reflection_time - budget.time_used),
            "memory_cost": budget.memory_cost,
            "memory_cost_remaining": max(0.0, self.config.max_memory_access_cost - budget.memory_cost),
            "depth": budget.depth,
            "action_count": budget.action_count,
            "visited_states_count": len(budget.visited_states),
        }


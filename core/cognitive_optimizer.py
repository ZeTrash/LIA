"""CognitiveOptimizer: optimisations pour améliorer les performances (Phase 5).

Ce module implémente :
- Cache des décisions fréquentes
- Parallélisation des actions indépendantes
- Optimisation des prompts
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from collections import OrderedDict

from .cognitive_models import ActionPlan, Action, ActionType, RequestAnalysis

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrée de cache pour une décision."""

    plan: ActionPlan
    timestamp: float
    hit_count: int = 0


class DecisionCache:
    """Cache pour les décisions fréquentes."""

    def __init__(self, max_size: int = 100, ttl_seconds: float = 3600.0):
        """
        Initialise le cache.

        Args:
            max_size: Taille maximale du cache
            ttl_seconds: Durée de vie des entrées (secondes)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[ActionPlan]:
        """
        Récupère un plan depuis le cache.

        Args:
            key: Clé de cache

        Returns:
            Plan si trouvé et valide, None sinon
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Vérifier TTL
        if time.time() - entry.timestamp > self.ttl_seconds:
            # Expiré, supprimer
            del self.cache[key]
            self.misses += 1
            return None

        # Hit: mettre à jour et déplacer en fin (LRU)
        entry.hit_count += 1
        self.cache.move_to_end(key)
        self.hits += 1
        return entry.plan

    def put(self, key: str, plan: ActionPlan) -> None:
        """
        Ajoute un plan au cache.

        Args:
            key: Clé de cache
            plan: Plan à mettre en cache
        """
        # Si cache plein, supprimer le plus ancien (LRU)
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[key] = CacheEntry(plan=plan, timestamp=time.time())

    def _create_key(self, message: str, analysis: RequestAnalysis) -> str:
        """Crée une clé de cache basée sur le message et l'analyse."""
        # Utiliser un hash du message + caractéristiques de l'analyse
        key_data = f"{message.lower().strip()}:{analysis.complexity}:{analysis.needs_memory}:{analysis.needs_identity}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class CognitiveOptimizer:
    """Optimiseur pour le système cognitif."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'optimiseur.

        Args:
            config: Configuration
        """
        self.config = config or {}

        # Cache des décisions
        cache_size = self.config.get("cache_size", 100)
        cache_ttl = self.config.get("cache_ttl_seconds", 3600.0)
        self.decision_cache = DecisionCache(
            max_size=cache_size, ttl_seconds=cache_ttl
        )

        # Configuration
        self.enable_cache = self.config.get("enable_cache", True)
        self.enable_parallelization = self.config.get("enable_parallelization", True)
        self.enable_prompt_optimization = self.config.get(
            "enable_prompt_optimization", True
        )

        logger.info("CognitiveOptimizer initialisé")

    def get_cached_plan(
        self, message: str, analysis: RequestAnalysis
    ) -> Optional[ActionPlan]:
        """
        Récupère un plan depuis le cache si disponible.

        Args:
            message: Message utilisateur
            analysis: Analyse de la requête

        Returns:
            Plan si trouvé, None sinon
        """
        if not self.enable_cache:
            return None
        
        logger.debug(f"🔍 [OPTIMIZER] Recherche dans le cache...")

        key = self.decision_cache._create_key(message, analysis)
        return self.decision_cache.get(key)

    def cache_plan(
        self, message: str, analysis: RequestAnalysis, plan: ActionPlan
    ) -> None:
        """
        Met un plan en cache.

        Args:
            message: Message utilisateur
            analysis: Analyse de la requête
            plan: Plan à mettre en cache
        """
        if not self.enable_cache:
            return

        logger.debug(f"💾 [OPTIMIZER] Mise en cache du plan: {len(plan.actions)} actions")
        key = self.decision_cache._create_key(message, analysis)
        self.decision_cache.put(key, plan)
        stats = self.decision_cache.get_stats()
        logger.debug(
            f"  📊 [OPTIMIZER] Cache stats: {stats['size']}/{stats['max_size']} entrées, hit_rate={stats['hit_rate']:.1f}%"
        )

    def identify_parallelizable_actions(
        self, plan: ActionPlan
    ) -> List[List[Action]]:
        """
        Identifie les actions qui peuvent être exécutées en parallèle.

        Args:
            plan: Plan d'actions

        Returns:
            Liste de groupes d'actions parallélisables
        """
        if not self.enable_parallelization:
            return [[action] for action in plan.sorted_actions()]

        # Actions qui peuvent être parallélisées (indépendantes)
        parallelizable_types = {
            ActionType.CONSULT_IDENTITY,
            ActionType.CONSULT_TRAITS,
            ActionType.CONSULT_ENVIRONMENT,
            ActionType.CONSULT_MEMORIES,
            ActionType.CONSULT_INTERACTIONS,
        }

        # Grouper les actions par priorité et type
        groups: List[List[Action]] = []
        current_group: List[Action] = []

        for action in plan.sorted_actions():
            # Actions parallélisables peuvent être groupées
            if action.type in parallelizable_types:
                current_group.append(action)
            else:
                # Action non parallélisable, créer un nouveau groupe
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([action])

        # Ajouter le dernier groupe
        if current_group:
            groups.append(current_group)

        return groups

    def optimize_prompt(
        self, prompt: str, max_length: Optional[int] = None
    ) -> str:
        """
        Optimise un prompt pour réduire sa taille si nécessaire.

        Args:
            prompt: Prompt original
            max_length: Longueur maximale (optionnel)

        Returns:
            Prompt optimisé
        """
        if not self.enable_prompt_optimization:
            return prompt

        if max_length is None:
            return prompt

        # Si le prompt est déjà assez court, ne rien faire
        if len(prompt) <= max_length:
            return prompt

        # Simplifier le prompt (truncation intelligente)
        # Pour l'instant, tronquer simplement
        # TODO: Implémenter une troncature plus intelligente
        optimized = prompt[:max_length]
        logger.debug(
            f"Prompt optimisé: {len(prompt)} -> {len(optimized)} caractères"
        )

        return optimized

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'optimisation."""
        stats = {
            "cache": self.decision_cache.get_stats(),
            "parallelization_enabled": self.enable_parallelization,
            "prompt_optimization_enabled": self.enable_prompt_optimization,
        }

        return stats


"""MemoryManager: gestion intelligente et sélective de la mémoire (Phase 4).

Le MemoryManager décide quoi mémoriser au lieu de tout stocker automatiquement.
Il analyse l'importance des interactions et extrait les informations clés.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """Élément à mémoriser."""

    content: str
    category: str  # "fact", "preference", "alert", "context"
    importance_score: float  # 0.0 - 1.0
    tags: List[str] = None
    ttl_days: int = 30  # Durée de vie par défaut

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryManager:
    """Gestionnaire de mémoire intelligent et sélectif."""

    def __init__(
        self,
        memory_adapter,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise le gestionnaire de mémoire.

        Args:
            memory_adapter: Adaptateur mémoire (MemoryAdapter)
            config: Configuration
        """
        self.memory = memory_adapter
        self.config = config or {}

        # Seuils de configuration
        self.min_importance_score = self.config.get("min_importance_score", 0.6)
        self.max_memories_per_interaction = self.config.get(
            "max_memories_per_interaction", 3
        )
        self.enable_auto_cleanup = self.config.get("enable_auto_cleanup", True)

        # Mots-clés indicateurs d'importance
        self.importance_keywords = {
            "high": [
                "important",
                "crucial",
                "remember",
                "never forget",
                "always",
                "preference",
                "favorite",
                "dislike",
                "hate",
                "love",
                "goal",
                "objective",
                "mission",
            ],
            "medium": [
                "like",
                "prefer",
                "usually",
                "often",
                "sometimes",
                "context",
                "background",
                "information",
            ],
        }

        logger.info("MemoryManager initialisé")

    async def decide_what_to_store(
        self,
        interaction: Dict[str, Any],
        execution_result: Optional[Any] = None,
        verification_result: Optional[Any] = None,
    ) -> List[MemoryItem]:
        """
        Décide quels éléments de l'interaction doivent être mémorisés.

        Args:
            interaction: Dictionnaire avec 'prompt', 'response', 'session_id', etc.
            execution_result: Résultat d'exécution (optionnel)
            verification_result: Résultat de vérification (optionnel)

        Returns:
            Liste des éléments à mémoriser (peut être vide)
        """
        logger.info(f"💾 [MEMORY_MANAGER] Analyse de l'interaction pour décision de mémorisation...")
        items_to_store: List[MemoryItem] = []

        # Analyser l'importance globale de l'interaction
        importance = self._analyze_importance(interaction)
        logger.debug(f"  📊 [MEMORY_MANAGER] Score d'importance: {importance:.2f} (seuil: {self.min_importance_score})")

        # Si l'importance est trop faible, ne rien mémoriser
        if importance < self.min_importance_score:
            logger.debug(
                f"  ⚠️  [MEMORY_MANAGER] Interaction non mémorisée (importance={importance:.2f} < {self.min_importance_score})"
            )
            return items_to_store

        # Extraire les informations clés
        logger.debug(f"  🔍 [MEMORY_MANAGER] Extraction des informations clés...")
        key_infos = self._extract_key_information(interaction)
        logger.debug(f"  ✅ [MEMORY_MANAGER] {len(key_infos)} informations clés extraites")

        # Créer des MemoryItem pour chaque information clé
        for info in key_infos[: self.max_memories_per_interaction]:
            category = self._categorize_information(info, interaction)
            item = MemoryItem(
                content=info,
                category=category,
                importance_score=importance,
                tags=self._extract_tags(info, interaction),
                ttl_days=self._calculate_ttl(importance, category),
            )
            items_to_store.append(item)

        logger.info(
            f"✅ [MEMORY_MANAGER] {len(items_to_store)} élément(s) à mémoriser (importance={importance:.2f})"
        )
        for idx, item in enumerate(items_to_store, 1):
            logger.debug(f"  📝 [MEMORY_MANAGER] Item {idx}: {item.category} (score: {item.importance_score:.2f}, TTL: {item.ttl_days}j)")

        return items_to_store

    def _analyze_importance(
        self, interaction: Dict[str, Any]
    ) -> float:
        """
        Analyse l'importance d'une interaction.

        Returns:
            Score d'importance entre 0.0 et 1.0
        """
        prompt = interaction.get("prompt", "").lower()
        response = interaction.get("response", "").lower()
        combined_text = f"{prompt} {response}"

        score = 0.0

        # 1. Vérifier les mots-clés d'importance élevée
        high_keywords_found = sum(
            1 for keyword in self.importance_keywords["high"] if keyword in combined_text
        )
        if high_keywords_found > 0:
            score += min(0.5, high_keywords_found * 0.15)

        # 2. Vérifier les mots-clés d'importance moyenne
        medium_keywords_found = sum(
            1
            for keyword in self.importance_keywords["medium"]
            if keyword in combined_text
        )
        if medium_keywords_found > 0:
            score += min(0.3, medium_keywords_found * 0.1)

        # 3. Longueur de l'interaction (interactions longues souvent plus importantes)
        text_length = len(combined_text)
        if text_length > 500:
            score += 0.1
        elif text_length > 200:
            score += 0.05

        # 4. Présence de questions directes sur l'identité/préférences
        identity_questions = [
            "qui es-tu",
            "what are you",
            "comment tu",
            "how do you",
            "préférence",
            "preference",
            "aime",
            "like",
            "déteste",
            "hate",
        ]
        if any(q in prompt for q in identity_questions):
            score += 0.2

        # 5. Présence de déclarations de préférence explicites
        preference_patterns = [
            r"j'?aime (?:bien |beaucoup )?(.+)",
            r"i (?:really )?like (.+)",
            r"je (?:n'?)?aime (?:pas )?(.+)",
            r"i (?:don'?t )?like (.+)",
            r"je préfère (.+)",
            r"i prefer (.+)",
        ]
        for pattern in preference_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                score += 0.15
                break

        # 6. Présence de faits ou informations importantes
        fact_indicators = [
            "souviens-toi",
            "remember",
            "important",
            "crucial",
            "never forget",
        ]
        if any(indicator in prompt for indicator in fact_indicators):
            score += 0.25

        # Normaliser le score entre 0.0 et 1.0
        return min(1.0, max(0.0, score))

    def _extract_key_information(
        self, interaction: Dict[str, Any]
    ) -> List[str]:
        """
        Extrait les informations clés d'une interaction.

        Returns:
            Liste des informations clés extraites
        """
        prompt = interaction.get("prompt", "")
        response = interaction.get("response", "")
        key_infos: List[str] = []

        # 1. Extraire les préférences explicites
        preference_patterns = [
            (r"j'?aime (?:bien |beaucoup )?(.+)", "J'aime {match}"),
            (r"je préfère (.+)", "Je préfère {match}"),
            (r"je (?:n'?)?aime (?:pas )?(.+)", "Je n'aime pas {match}"),
            (r"i (?:really )?like (.+)", "I like {match}"),
            (r"i prefer (.+)", "I prefer {match}"),
            (r"i (?:don'?t )?like (.+)", "I don't like {match}"),
        ]

        for pattern, template in preference_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                key_infos.append(template.format(match=match.strip()))

        # 2. Extraire les faits importants (indiqués explicitement)
        fact_patterns = [
            (r"souviens-toi (?:que |qu'?)(.+)", "Fait: {match}"),
            (r"remember (?:that )?(.+)", "Fact: {match}"),
            (r"important[:\s]+(.+)", "Important: {match}"),
        ]

        for pattern, template in fact_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                key_infos.append(template.format(match=match.strip()[:200]))

        # 3. Extraire les informations contextuelles de la réponse
        # (si la réponse contient des informations structurées)
        if len(response) > 50 and len(response) < 500:
            # Si la réponse est concise et informative, la considérer comme clé
            key_infos.append(f"Contexte: {response[:200]}")

        # 4. Si aucune information clé n'a été extraite mais l'interaction est importante,
        # extraire un résumé
        if not key_infos and len(prompt) > 20:
            # Créer un résumé simple
            summary = f"Interaction: {prompt[:100]}"
            if len(response) > 0:
                summary += f" → {response[:100]}"
            key_infos.append(summary)

        return key_infos

    def _categorize_information(
        self, info: str, interaction: Dict[str, Any]
    ) -> str:
        """
        Catégorise une information.

        Returns:
            Catégorie: "fact", "preference", "alert", "context"
        """
        info_lower = info.lower()

        # Préférences
        if any(
            word in info_lower
            for word in ["aime", "like", "préfère", "prefer", "déteste", "hate"]
        ):
            return "preference"

        # Alertes
        if any(word in info_lower for word in ["alerte", "alert", "attention", "warning"]):
            return "alert"

        # Faits
        if any(
            word in info_lower
            for word in ["fait", "fact", "important", "souviens", "remember"]
        ):
            return "fact"

        # Par défaut: contexte
        return "context"

    def _extract_tags(
        self, info: str, interaction: Dict[str, Any]
    ) -> List[str]:
        """
        Extrait des tags pertinents pour une information.

        Returns:
            Liste de tags
        """
        tags: List[str] = []
        info_lower = info.lower()

        # Tags basés sur le contenu
        content_tags = {
            "personnalité": ["personnalité", "personality", "traits", "caractère"],
            "préférence": ["aime", "like", "préfère", "prefer"],
            "contexte": ["contexte", "context", "background"],
            "identité": ["qui", "who", "identité", "identity"],
        }

        for tag, keywords in content_tags.items():
            if any(keyword in info_lower for keyword in keywords):
                tags.append(tag)

        # Tags basés sur la session (si disponible)
        session_id = interaction.get("session_id")
        if session_id:
            tags.append(f"session:{session_id[:8]}")

        return tags

    def _calculate_ttl(self, importance: float, category: str) -> int:
        """
        Calcule la durée de vie (TTL) en jours pour une information.

        Args:
            importance: Score d'importance (0.0 - 1.0)
            category: Catégorie de l'information

        Returns:
            TTL en jours
        """
        # TTL de base selon la catégorie
        base_ttl = {
            "preference": 90,  # Préférences durent longtemps
            "fact": 60,  # Faits durent moyennement
            "alert": 7,  # Alertes sont temporaires
            "context": 30,  # Contexte est temporaire
        }.get(category, 30)

        # Ajuster selon l'importance
        if importance >= 0.8:
            return int(base_ttl * 1.5)  # Très important = durée plus longue
        elif importance >= 0.6:
            return base_ttl
        else:
            return int(base_ttl * 0.7)  # Moins important = durée plus courte

    async def store_memories(
        self, items: List[MemoryItem], session_id: Optional[str] = None
    ) -> List[str]:
        """
        Stocke les éléments mémorisés dans la base de données.

        Args:
            items: Liste des MemoryItem à stocker
            session_id: ID de session (optionnel)

        Returns:
            Liste des IDs des souvenirs créés
        """
        if not self.memory:
            logger.warning("MemoryAdapter non disponible, impossible de stocker")
            return []

        memory_ids: List[str] = []
        for item in items:
            try:
                memory_id = self.memory.add_memory_from_interaction(
                    content=item.content,
                    category=item.category,
                    importance_score=item.importance_score,
                )
                if memory_id:
                    memory_ids.append(memory_id)
                    logger.debug(
                        f"✅ Mémoire stockée: {item.category} (importance={item.importance_score:.2f})"
                    )
            except Exception as e:
                logger.error(f"Erreur lors du stockage d'une mémoire: {e}")

        return memory_ids

    async def cleanup_old_memories(
        self, older_than_days: int = 90
    ) -> int:
        """
        Nettoie les souvenirs obsolètes.

        Args:
            older_than_days: Supprimer les souvenirs plus anciens que X jours

        Returns:
            Nombre de souvenirs supprimés
        """
        if not self.enable_auto_cleanup:
            return 0

        # Cette fonctionnalité nécessiterait une extension de MemoryStore
        # Pour l'instant, on retourne 0 (non implémenté)
        logger.debug(f"Nettoyage automatique non implémenté (older_than_days={older_than_days})")
        return 0


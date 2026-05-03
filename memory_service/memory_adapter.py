"""Adaptateur mémoire pour intégration avec le noyau primaire."""

import logging
from typing import Dict, Any, Optional
import uuid

from .store import MemoryStore

logger = logging.getLogger(__name__)


class MemoryAdapter:
    """Adaptateur pour intégrer la mémoire avec le noyau primaire."""
    
    def __init__(self):
        """Initialise l'adaptateur mémoire."""
        self.store = MemoryStore()
        logger.info("MemoryAdapter initialisé")
    
    def get_context(self, limit_traits: int = 10, limit_memories: int = 10, limit_interactions: int = 5) -> Dict[str, Any]:
        """
        Récupère le contexte mémoire pour le noyau primaire.
        
        Args:
            limit_traits: Nombre maximum de traits
            limit_memories: Nombre maximum de souvenirs
            limit_interactions: Nombre maximum d'interactions récentes
        
        Returns:
            Contexte formaté pour le noyau primaire
        """
        try:
            context = self.store.get_context(limit_traits, limit_memories, limit_interactions)
            logger.debug(f"Contexte récupéré: {len(context['traits'])} traits, {len(context['memories'])} souvenirs, {len(context.get('recent_interactions', []))} interactions")
            return context
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contexte: {e}")
            # Retourner un contexte vide en cas d'erreur
            return {
                "traits": [],
                "memories": [],
                "recent_interactions": [],
                "session_goals": []
            }
    
    def log_interaction(
        self,
        session_id: str,
        prompt: str,
        response: str,
        scores: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """
        Journalise une interaction.
        
        Args:
            session_id: ID de session
            prompt: Prompt de l'utilisateur
            response: Réponse générée
            scores: Scores optionnels
            severity: Sévérité
        
        Returns:
            ID de l'interaction journalisée
        """
        try:
            interaction_id = self.store.log_interaction(
                session_id=session_id,
                prompt=prompt,
                response=response,
                scores=scores,
                severity=severity
            )
            logger.debug(f"Interaction journalisée: {interaction_id}")
            return interaction_id
        except Exception as e:
            logger.error(f"Erreur lors de la journalisation: {e}")
            return None
    
    def add_memory_from_interaction(
        self,
        content: str,
        category: str = "fact",
        importance_score: float = 0.5
    ) -> Optional[str]:
        """
        Ajoute un souvenir basé sur une interaction.
        
        Args:
            content: Contenu du souvenir
            category: Catégorie (fact, preference, alert)
            importance_score: Score d'importance
        
        Returns:
            ID du souvenir créé
        """
        try:
            memory_id = self.store.add_memory(
                category=category,
                content=content,
                importance_score=importance_score
            )
            logger.info(f"Souvenir créé depuis interaction: {memory_id}")
            return memory_id
        except Exception as e:
            logger.error(f"Erreur lors de la création du souvenir: {e}")
            return None

    # ------------------------------------------------------------------
    # Patterns (seed/fake + apprentissage futur)
    # ------------------------------------------------------------------

    def list_theme_patterns(self) -> list:
        """Retourne la liste des noms de thèmes disponibles (V2)."""
        try:
            return self.store.list_theme_patterns()
        except Exception as e:
            logger.error(f"Erreur list_theme_patterns: {e}")
            return []

    def get_theme_examples(self, limit_per_theme: int = 2) -> dict:
        """Retourne des exemples de patterns par thème (V2)."""
        try:
            return self.store.get_theme_examples(limit_per_theme=limit_per_theme)
        except Exception as e:
            logger.error(f"Erreur get_theme_examples: {e}")
            return {}

    def add_theme_pattern(self, theme_name: str) -> Optional[str]:
        """Ajoute un thème s'il n'existe pas (V2)."""
        try:
            return self.store.add_theme_pattern(theme_name=theme_name)
        except Exception as e:
            logger.error(f"Erreur add_theme_pattern: {e}")
            return None

    def upsert_pattern(
        self,
        menu_context: str,
        prev_step: str,
        recommended_step: str,
        weights: Optional[Dict[str, float]] = None,
        source: str = "seed",
        confidence: float = 0.5,
        theme_pattern: Optional[str] = None,
    ) -> Optional[str]:
        try:
            return self.store.upsert_pattern(
                menu_context=menu_context,
                prev_step=prev_step,
                recommended_step=recommended_step,
                weights=weights,
                source=source,
                confidence=confidence,
                theme_pattern=theme_pattern,
            )
        except Exception as e:
            logger.error(f"Erreur upsert_pattern: {e}")
            return None

    def get_pattern_recommendation(
        self,
        menu_context: str,
        prev_step: str,
        theme_pattern: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            return self.store.get_pattern_recommendation(
                menu_context=menu_context,
                prev_step=prev_step,
                theme_pattern=theme_pattern,
            )
        except Exception as e:
            logger.error(f"Erreur get_pattern_recommendation: {e}")
            return None


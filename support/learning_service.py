"""Service d'apprentissage via le noyau d'appui (Gemini)."""

import logging
from typing import Dict, Any, Optional
import uuid

from .gemini_adapter import GeminiAdapter
from .config import SupportConfig

logger = logging.getLogger(__name__)

# Import optionnel de la mémoire
try:
    from memory_service.memory_adapter import MemoryAdapter
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Service mémoire non disponible pour l'apprentissage")


class LearningService:
    """Service permettant à LIA d'apprendre via le noyau d'appui."""
    
    def __init__(
        self,
        gemini_adapter: Optional[GeminiAdapter] = None,
        memory_adapter: Optional[MemoryAdapter] = None,
        config: Optional[SupportConfig] = None
    ):
        """
        Initialise le service d'apprentissage.
        
        Args:
            gemini_adapter: Adaptateur Gemini (optionnel, créé si None)
            memory_adapter: Adaptateur mémoire (optionnel, créé si None)
            config: Configuration du noyau d'appui (optionnel)
        """
        self.config = config or SupportConfig()
        
        # Initialiser Gemini
        self.gemini = gemini_adapter or GeminiAdapter(self.config)
        
        # Initialiser la mémoire si disponible
        self.memory = None
        if memory_adapter:
            self.memory = memory_adapter
        elif MEMORY_AVAILABLE:
            try:
                self.memory = MemoryAdapter()
                logger.info("✅ Mémoire intégrée au service d'apprentissage")
            except Exception as e:
                logger.warning(f"⚠️  Impossible d'initialiser la mémoire: {e}")
        
        logger.info("LearningService initialisé")
    
    async def learn(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        save_to_memory: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Permet à LIA d'apprendre en interrogeant Gemini.
        
        Args:
            question: Question à poser à Gemini
            context: Contexte optionnel (traits, souvenirs, etc.)
            save_to_memory: Sauvegarder la connaissance dans la mémoire (défaut: auto_save_knowledge)
        
        Returns:
            Dictionnaire avec la réponse et les métadonnées
        """
        if not self.config.enable_learning:
            raise RuntimeError("L'apprentissage est désactivé dans la configuration")
        
        if not self.gemini.is_available():
            raise RuntimeError("Gemini API non disponible")
        
        try:
            # Interroger Gemini
            logger.info(f"🔍 LIA apprend via Gemini: {question[:50]}...")
            answer = await self.gemini.query(question, context)
            
            result = {
                "question": question,
                "answer": answer,
                "source": "gemini",
                "learned_at": None,
                "memory_id": None
            }
            
            # Sauvegarder dans la mémoire si activé
            should_save = save_to_memory if save_to_memory is not None else self.config.auto_save_knowledge
            if should_save and self.memory:
                try:
                    # Créer un souvenir avec la connaissance apprise
                    knowledge_content = f"Question: {question}\nRéponse: {answer}"
                    memory_id = self.memory.add_memory_from_interaction(
                        content=knowledge_content,
                        category="fact",
                        importance_score=0.7
                    )
                    result["memory_id"] = memory_id
                    result["learned_at"] = "now"
                    logger.info(f"✅ Connaissance sauvegardée dans la mémoire: {memory_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Erreur lors de la sauvegarde dans la mémoire: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'apprentissage: {e}")
            raise
    
    async def explore_topic(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Permet à LIA d'explorer un sujet en profondeur.
        
        Args:
            topic: Sujet à explorer
            context: Contexte optionnel
            depth: Profondeur d'exploration (1 = basique, 2+ = approfondi)
        
        Returns:
            Dictionnaire avec les connaissances apprises
        """
        questions = [
            f"Qu'est-ce que {topic} ?",
            f"Quels sont les aspects importants de {topic} ?",
            f"Comment {topic} fonctionne-t-il ?"
        ]
        
        # Limiter selon la profondeur
        questions = questions[:depth]
        
        results = []
        for question in questions:
            try:
                result = await self.learn(question, context, save_to_memory=True)
                results.append(result)
            except Exception as e:
                logger.warning(f"Erreur lors de l'exploration de '{question}': {e}")
        
        return {
            "topic": topic,
            "depth": depth,
            "learnings": results,
            "count": len(results)
        }


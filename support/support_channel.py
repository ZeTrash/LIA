"""Canal d'échange avec le noyau d'appui (Gemini).

Ce canal permet à LIA d'interroger Gemini de manière structurée pour apprendre.
Il est séparé du canal utilisateur et intégré dans le cycle d'apprentissage autonome.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
import uuid

from .gemini_adapter import GeminiAdapter
from .groq_adapter import GroqAdapter
from .learning_service import LearningService
from .config import SupportConfig

logger = logging.getLogger(__name__)

# Import optionnel de la mémoire
try:
    from memory_service.memory_adapter import MemoryAdapter
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Service mémoire non disponible pour le canal support")


class SupportChannel:
    """Canal d'échange avec le noyau d'appui (Gemini).
    
    Ce canal permet à LIA d'interroger Gemini pour apprendre de manière autonome.
    Il est distinct du canal utilisateur et gère spécifiquement les interactions
    entre LIA et les sources de connaissance externes.
    """
    
    def __init__(
        self,
        gemini_adapter: Optional[GeminiAdapter] = None,
        groq_adapter: Optional[GroqAdapter] = None,
        learning_service: Optional[LearningService] = None,
        memory_adapter: Optional[MemoryAdapter] = None,
        config: Optional[SupportConfig] = None
    ):
        """
        Initialise le canal d'échange avec le noyau d'appui.
        
        Args:
            gemini_adapter: Adaptateur Gemini (optionnel)
            groq_adapter: Adaptateur Groq (optionnel, préféré si disponible)
            learning_service: Service d'apprentissage (optionnel, créé si None)
            memory_adapter: Adaptateur mémoire (optionnel, créé si None)
            config: Configuration du noyau d'appui (optionnel)
        """
        self.config = config or SupportConfig()
        
        # Initialiser les services
        if learning_service:
            self.learning_service = learning_service
            self.gemini = learning_service.gemini
            self.groq = None  # LearningService utilise Gemini pour l'instant
        elif groq_adapter:
            # Préférer Groq si disponible
            self.groq = groq_adapter
            self.gemini = gemini_adapter  # Garder Gemini comme fallback
            self.learning_service = None  # LearningService utilise Gemini pour l'instant
        elif gemini_adapter:
            self.gemini = gemini_adapter
            self.groq = None
            # Créer LearningService si mémoire disponible
            if memory_adapter or MEMORY_AVAILABLE:
                memory = memory_adapter or (MemoryAdapter() if MEMORY_AVAILABLE else None)
                self.learning_service = LearningService(
                    gemini_adapter=gemini_adapter,
                    memory_adapter=memory,
                    config=self.config
                )
            else:
                self.learning_service = None
        else:
            # Créer les adaptateurs si non fournis (préférer Groq)
            if not self.config.groq_api_key:
                self.config.load_from_file()
            if self.config.groq_api_key and self.config.groq_api_key != "YOUR_GROQ_API_KEY_HERE":
                self.groq = GroqAdapter(self.config)
                self.gemini = GeminiAdapter(self.config)  # Fallback
            else:
                self.gemini = GeminiAdapter(self.config)
                self.groq = None
            
            if memory_adapter or MEMORY_AVAILABLE:
                memory = memory_adapter or (MemoryAdapter() if MEMORY_AVAILABLE else None)
                # LearningService utilise Gemini pour l'instant
                adapter_for_learning = self.gemini
                self.learning_service = LearningService(
                    gemini_adapter=adapter_for_learning,
                    memory_adapter=memory,
                    config=self.config
                )
            else:
                self.learning_service = None
        
        # Historique des échanges (pour contexte)
        self.exchange_history: List[Dict[str, Any]] = []
        self.max_history = 10  # Garder les 10 derniers échanges
        
        # Callback optionnel pour le streaming temps réel vers l'interface
        # Signature attendue: async def cb(event: str, payload: Dict[str, Any]) -> None
        self.stream_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
        
        logger.info("✅ SupportChannel initialisé")
    
    def set_stream_callback(
        self,
        callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]]
    ) -> None:
        """Enregistre un callback asynchrone pour le streaming temps réel.
        
        Le callback est appelé à chaque requête/réponse Gemini avec:
        - event: "gemini_query", "gemini_response" ou "gemini_error"
        - payload: dictionnaire avec au minimum question / answer / error / session_id / timestamp
        """
        self.stream_callback = callback
    
    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        save_to_memory: bool = True,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interroge le noyau d'appui (Gemini) via le canal dédié.
        
        Args:
            question: Question à poser à Gemini
            context: Contexte optionnel (traits, souvenirs, etc.)
            save_to_memory: Sauvegarder l'échange dans la mémoire (défaut: True)
            session_id: ID de session pour la journalisation
        
        Returns:
            Dictionnaire avec la réponse et les métadonnées de l'échange
        """
        if not self.gemini.is_available():
            raise RuntimeError("Gemini API non disponible")
        
        exchange_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        logger.info(f"📡 Canal Support: LIA interroge Gemini - {question[:50]}...")
        
        # Notifier l'interface qu'une requête à Gemini démarre
        if self.stream_callback:
            try:
                asyncio.create_task(self.stream_callback("gemini_query", {
                    "exchange_id": exchange_id,
                    "timestamp": timestamp,
                    "question": question,
                    "context": context,
                    "session_id": session_id,
                }))
            except Exception as cb_err:
                logger.debug(f"Callback de streaming (gemini_query) ignoré: {cb_err}")
        
        try:
            # Utiliser le streaming si un callback est configuré
            use_streaming = self.stream_callback is not None
            
            if use_streaming:
                # Streaming en temps réel
                answer_chunks = []
                
                async def stream_chunk_callback(chunk: str):
                    """Callback pour chaque chunk reçu."""
                    answer_chunks.append(chunk)
                    # Envoyer le chunk en temps réel via le callback de streaming
                    if self.stream_callback:
                        try:
                            await self.stream_callback("gemini_chunk", {
                                "exchange_id": exchange_id,
                                "timestamp": datetime.now().isoformat(),
                                "chunk": chunk,
                                "session_id": session_id,
                            })
                        except Exception as cb_err:
                            logger.debug(f"Erreur callback streaming chunk: {cb_err}")
                
                # Utiliser query_stream pour obtenir les chunks en temps réel
                answer = ""
                async for chunk in self.gemini.query_stream(question, context, stream_chunk_callback):
                    answer += chunk
                
                # Sauvegarder dans la mémoire si nécessaire
                memory_id = None
                if save_to_memory and self.learning_service and self.learning_service.memory:
                    try:
                        # Sauvegarder la connaissance apprise dans la mémoire
                        knowledge_content = f"Question: {question}\nRéponse: {answer}"
                        memory_id = self.learning_service.memory.add_memory_from_interaction(
                            content=knowledge_content,
                            category="fact",
                            importance_score=0.7
                        )
                        logger.debug(f"Connaissance sauvegardée dans la mémoire (ID: {memory_id})")
                    except Exception as mem_err:
                        logger.warning(f"Erreur sauvegarde mémoire après streaming: {mem_err}")
            else:
                # Mode non-streaming (comportement original)
                if self.learning_service:
                    result = await self.learning_service.learn(
                        question=question,
                        context=context,
                        save_to_memory=save_to_memory
                    )
                    answer = result.get("answer", "")
                    memory_id = result.get("memory_id")
                else:
                    # Fallback vers GeminiAdapter directement
                    answer = await self.gemini.query(question, context)
                    memory_id = None
            
            # Créer l'enregistrement d'échange
            exchange_record = {
                "exchange_id": exchange_id,
                "timestamp": timestamp,
                "question": question,
                "answer": answer,
                "context": context,
                "memory_id": memory_id,
                "session_id": session_id,
                "success": True,
                "error": None
            }
            
            # Ajouter à l'historique
            self.exchange_history.append(exchange_record)
            if len(self.exchange_history) > self.max_history:
                self.exchange_history.pop(0)
            
            logger.info(f"✅ Canal Support: Réponse reçue de Gemini (échange {exchange_id[:8]})")
            
            # Streaming temps réel de la réponse
            if self.stream_callback:
                try:
                    asyncio.create_task(self.stream_callback("gemini_response", exchange_record.copy()))
                except Exception as cb_err:
                    logger.debug(f"Callback de streaming (gemini_response) ignoré: {cb_err}")
            
            return {
                "exchange_id": exchange_id,
                "timestamp": timestamp,
                "question": question,
                "answer": answer,
                "context": context,
                "memory_id": memory_id,
                "source": "gemini",
                "channel": "support",
                "success": True
            }
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Erreur dans le canal Support: {e}")
            
            # Enregistrer l'échec dans l'historique pour traçabilité
            exchange_record = {
                "exchange_id": exchange_id,
                "timestamp": timestamp,
                "question": question,
                "answer": None,
                "context": context,
                "memory_id": None,
                "session_id": session_id,
                "success": False,
                "error": error_message
            }
            
            # Ajouter à l'historique même en cas d'erreur
            self.exchange_history.append(exchange_record)
            if len(self.exchange_history) > self.max_history:
                self.exchange_history.pop(0)
            
            logger.warning(f"⚠️  Échange enregistré dans l'historique malgré l'erreur (échange {exchange_id[:8]})")
            
            # Relancer l'exception pour que l'appelant puisse gérer
            raise
    
    async def explore_topic(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        depth: int = 1,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explore un sujet en profondeur via le canal support.
        
        Args:
            topic: Sujet à explorer
            context: Contexte optionnel
            depth: Profondeur d'exploration (1 = basique, 2+ = approfondi)
            session_id: ID de session
        
        Returns:
            Dictionnaire avec les connaissances apprises
        """
        if not self.learning_service:
            raise RuntimeError("LearningService non disponible pour l'exploration")
        
        logger.info(f"🔍 Canal Support: Exploration du sujet '{topic}' (profondeur {depth})")
        
        result = await self.learning_service.explore_topic(
            topic=topic,
            context=context,
            depth=depth
        )
        
        # Ajouter les échanges à l'historique
        for learning in result.get("learnings", []):
            exchange_record = {
                "exchange_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "question": learning.get("question", ""),
                "answer": learning.get("answer", ""),
                "context": context,
                "memory_id": learning.get("memory_id"),
                "session_id": session_id,
                "exploration": True,
                "topic": topic
            }
            self.exchange_history.append(exchange_record)
            if len(self.exchange_history) > self.max_history:
                self.exchange_history.pop(0)
        
        logger.info(f"✅ Canal Support: Exploration terminée ({result.get('count', 0)} connaissances apprises)")
        
        return result
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des échanges.
        
        Args:
            limit: Nombre maximum d'échanges à retourner (défaut: tous)
        
        Returns:
            Liste des échanges récents
        """
        if limit:
            return self.exchange_history[-limit:]
        return self.exchange_history.copy()
    
    def clear_history(self):
        """Efface l'historique des échanges."""
        self.exchange_history.clear()
        logger.debug("Historique du canal Support effacé")
    
    def is_available(self) -> bool:
        """
        Vérifie si le canal est disponible.
        
        Returns:
            True si Gemini est disponible, False sinon
        """
        return self.gemini.is_available() if self.gemini else False


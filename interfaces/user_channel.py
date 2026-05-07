"""Canal d'interaction avec l'utilisateur.

Ce canal permet à l'utilisateur d'interagir avec LIA de manière structurée.
Il est séparé du canal noyau d'appui et gère spécifiquement les interactions humaines.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Import optionnel des composants
try:
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    logger.warning("Core non disponible pour le canal utilisateur")

try:
    from memory_service.memory_adapter import MemoryAdapter
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Mémoire non disponible pour le canal utilisateur")

try:
    from support.support_channel import SupportChannel
    SUPPORT_CHANNEL_AVAILABLE = True
except ImportError:
    SUPPORT_CHANNEL_AVAILABLE = False
    logger.warning("SupportChannel non disponible pour le canal utilisateur")


class UserChannel:
    """Canal d'interaction avec l'utilisateur.
    
    Ce canal permet à l'utilisateur d'interagir avec LIA de manière structurée.
    Il gère les interactions humaines, la journalisation et l'utilisation du contexte mémoire.
    """
    
    def __init__(
        self,
        core_adapter: Optional[LLMAdapter] = None,
        memory_adapter: Optional[MemoryAdapter] = None,
        support_channel: Optional[SupportChannel] = None,
        core_config: Optional[CoreConfig] = None
    ):
        """
        Initialise le canal utilisateur.
        
        Args:
            core_adapter: Adaptateur du noyau primaire (optionnel, créé si None)
            memory_adapter: Adaptateur mémoire (optionnel, créé si None)
            support_channel: Canal Support pour autonomie (optionnel)
            core_config: Configuration du noyau primaire (optionnel)
        """
        if not CORE_AVAILABLE:
            raise RuntimeError("Core non disponible - impossible de créer UserChannel")
        
        # Initialiser la mémoire si disponible
        self.memory = None
        if memory_adapter:
            self.memory = memory_adapter
        elif MEMORY_AVAILABLE:
            try:
                self.memory = MemoryAdapter()
                logger.info("✅ Mémoire intégrée au canal utilisateur")
            except Exception as e:
                logger.warning(f"⚠️  Impossible d'initialiser la mémoire: {e}")
        
        # Initialiser le noyau primaire
        if core_adapter:
            self.core_adapter = core_adapter
        else:
            if not core_config:
                core_config = CoreConfig()
            # Créer LLMAdapter avec support_channel si disponible
            # Activer le système de planification cognitive (Phase 2-6)
            # et le traitement par phrases (MemoryRank V2) pour les interactions utilisateur.
            self.core_adapter = LLMAdapter(
                config=core_config,
                use_memory=True,
                support_channel=support_channel,
                use_cognitive_planner=True,  # Activer le nouveau système
                use_phrase_memory=True,      # Activer MemoryRank V2 (traitement par phrases)
            )
            logger.info("✅ Noyau primaire créé pour le canal utilisateur")
        
        self.support_channel = support_channel
        
        # Historique des interactions utilisateur
        self.interaction_history: List[Dict[str, Any]] = []
        self.max_history = 50  # Garder les 50 dernières interactions
        
        logger.info("✅ UserChannel initialisé")
    
    async def send_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_autonomy: bool = True,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Envoie un message à LIA et récupère sa réponse.
        
        Args:
            message: Message de l'utilisateur
            session_id: ID de session (optionnel, généré si None)
            use_autonomy: Activer l'autonomie (LIA peut solliciter Gemini) (défaut: True)
            stream_callback: Callback pour recevoir les chunks en streaming (optionnel)
        
        Returns:
            Dictionnaire avec la réponse et les métadonnées de l'interaction
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        interaction_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        logger.info(f"👤 Utilisateur: {message[:50]}...")
        
        try:
            # Utiliser le streaming si un callback est fourni
            if stream_callback:
                # Générer la réponse avec streaming
                response_chunks = []
                async for chunk in self.core_adapter.generate_stream(
                    message=message,
                    session_id=session_id,
                    stream_callback=stream_callback,
                    use_autonomy=use_autonomy
                ):
                    response_chunks.append(chunk)
                response = "".join(response_chunks)
            else:
                # Génération normale sans streaming
                response = await self.core_adapter.generate(
                    message=message,
                    session_id=session_id,
                    use_autonomy=use_autonomy
                )
            
            # Créer l'enregistrement d'interaction
            interaction_record = {
                "interaction_id": interaction_id,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_message": message,
                "lia_response": response,
                "success": True,
                "error": None
            }
            
            # Ajouter à l'historique
            self.interaction_history.append(interaction_record)
            if len(self.interaction_history) > self.max_history:
                self.interaction_history.pop(0)
            
            logger.info(f"✅ Réponse générée (interaction {interaction_id[:8]})")
            
            return {
                "interaction_id": interaction_id,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_message": message,
                "lia_response": response,
                "success": True
            }
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Erreur dans le canal utilisateur: {e}")
            
            # Enregistrer l'échec dans l'historique
            interaction_record = {
                "interaction_id": interaction_id,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_message": message,
                "lia_response": None,
                "success": False,
                "error": error_message
            }
            
            self.interaction_history.append(interaction_record)
            if len(self.interaction_history) > self.max_history:
                self.interaction_history.pop(0)
            
            raise
    
    async def send_message_structured(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_autonomy: bool = True,
        process_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Envoie un message à LIA et récupère à la fois:
        - la réponse finale,
        - la trace structurée du processus interne (menus, décisions, etc.).

        Cette méthode est destinée aux interfaces (ex: web) qui veulent afficher:
        - des messages de type "Processus" (étapes internes),
        - puis la "Response" finale à l'utilisateur.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        interaction_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        logger.info(f"👤 Utilisateur (structured): {message[:50]}...")

        try:

            async def _internal_process_callback(chunk_obj: Any):
                # chunk_obj est un ResponseChunk; on le transforme en dict sérialisable
                if not process_callback:
                    return
                try:
                    if isinstance(chunk_obj, dict):
                        # Some core paths emit already-serialized chunk dicts.
                        chunk_type = chunk_obj.get("type")
                        if hasattr(chunk_type, "value"):
                            chunk_type = chunk_type.value
                        chunk_dict = {
                            "type": chunk_type,
                            "content": chunk_obj.get("content", ""),
                            "metadata": chunk_obj.get("metadata", {}) or {},
                        }
                    else:
                        chunk_type = getattr(chunk_obj, "type", None)
                        if hasattr(chunk_type, "value"):
                            chunk_type = chunk_type.value
                        chunk_dict = {
                            "type": chunk_type,
                            "content": getattr(chunk_obj, "content", ""),
                            "metadata": getattr(chunk_obj, "metadata", {}) or {},
                        }
                    await process_callback(chunk_dict)
                except Exception as cb_err:
                    logger.debug(f"Erreur process_callback (user_channel): {cb_err}")

            result = await self.core_adapter.generate_with_trace(
                message=message,
                session_id=session_id,
                use_autonomy=use_autonomy,
                use_cognitive_planner=True,  # la trace n'a de sens que via le planner
                process_callback=_internal_process_callback,
            )

            response = result.get("response", "")
            trace = result.get("trace", [])

            # Loguer la trace structurée côté serveur pour observation
            if trace:
                logger.info("🧩 Trace structurée de l'interaction (processus interne) :")
                for chunk in trace:
                    try:
                        ctype = chunk.get("type")
                        content = (chunk.get("content") or "")[:200]
                        logger.info(f"  - {ctype}: {content}")
                    except Exception:
                        continue
            logger.info(f"💬 Réponse finale (structured): {response[:200]}")

            interaction_record = {
                "interaction_id": interaction_id,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_message": message,
                "lia_response": response,
                "trace": trace,
                "success": True,
                "error": None,
            }

            self.interaction_history.append(interaction_record)
            if len(self.interaction_history) > self.max_history:
                self.interaction_history.pop(0)

            logger.info(f"✅ Réponse structurée générée (interaction {interaction_id[:8]})")

            return interaction_record

        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Erreur dans le canal utilisateur (structured): {e}")

            interaction_record = {
                "interaction_id": interaction_id,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_message": message,
                "lia_response": None,
                "trace": [],
                "success": False,
                "error": error_message,
            }

            self.interaction_history.append(interaction_record)
            if len(self.interaction_history) > self.max_history:
                self.interaction_history.pop(0)

            raise
    
    def get_history(
        self,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des interactions.
        
        Args:
            session_id: Filtrer par session (optionnel)
            limit: Nombre maximum d'interactions à retourner (défaut: tous)
        
        Returns:
            Liste des interactions
        """
        history = self.interaction_history.copy()
        
        # Filtrer par session si spécifié
        if session_id:
            history = [h for h in history if h.get("session_id") == session_id]
        
        # Limiter si spécifié
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Récupère l'historique d'une session spécifique.
        
        Args:
            session_id: ID de la session
        
        Returns:
            Liste des interactions de la session
        """
        return self.get_history(session_id=session_id)
    
    def clear_history(self, session_id: Optional[str] = None):
        """
        Efface l'historique des interactions.
        
        Args:
            session_id: Effacer uniquement une session spécifique (optionnel)
        """
        if session_id:
            self.interaction_history = [
                h for h in self.interaction_history
                if h.get("session_id") != session_id
            ]
            logger.debug(f"Historique de la session {session_id} effacé")
        else:
            self.interaction_history.clear()
            logger.debug("Historique du canal utilisateur effacé")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère des statistiques sur les interactions.
        
        Returns:
            Dictionnaire avec les statistiques
        """
        total = len(self.interaction_history)
        successful = sum(1 for h in self.interaction_history if h.get("success", False))
        failed = total - successful
        
        # Compter les sessions uniques
        unique_sessions = len(set(h.get("session_id") for h in self.interaction_history))
        
        return {
            "total_interactions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "unique_sessions": unique_sessions
        }


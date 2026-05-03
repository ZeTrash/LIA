"""Système pour activer et solliciter la mémoire de LIA."""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

# Import optionnel de la mémoire
try:
    from memory_service.memory_adapter import MemoryAdapter
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Service mémoire non disponible")
    # Éviter NameError dans les annotations lorsque le service mémoire n'est pas importable
    MemoryAdapter = Any  # type: ignore[misc,assignment]

if TYPE_CHECKING:
    # Pour aider les IDE/type checkers sans casser l'exécution si l'import runtime échoue
    from memory_service.memory_adapter import MemoryAdapter as MemoryAdapterType


class MemoryActivator:
    """Active et sollicite la mémoire de LIA."""
    
    def __init__(self, memory_adapter: Optional["MemoryAdapter"] = None):
        """
        Initialise l'activateur de mémoire.
        
        Args:
            memory_adapter: Adaptateur mémoire (optionnel, peut être None)
        """
        self.memory = memory_adapter
        logger.info("MemoryActivator initialisé")
    
    def get_active_context(self, message: str, session_id: str, limit_traits: int = 10, limit_memories: int = 10, limit_interactions: int = 5) -> Dict[str, Any]:
        """
        Récupère un contexte actif en cherchant des souvenirs pertinents.
        
        Args:
            message: Message de l'utilisateur
            session_id: ID de session
            limit_traits: Nombre maximum de traits
            limit_memories: Nombre maximum de souvenirs
            limit_interactions: Nombre maximum d'interactions récentes
        
        Returns:
            Contexte enrichi avec souvenirs pertinents et historique
        """
        if not self.memory:
            return {
                "traits": [],
                "memories": [],
                "recent_interactions": [],
                "session_goals": []
            }
        
        # Récupérer le contexte de base (inclut maintenant les interactions)
        context = self.memory.get_context(limit_traits=limit_traits, limit_memories=limit_memories, limit_interactions=limit_interactions)
        
        # Log pour diagnostiquer
        logger.info(f"📚 MemoryActivator: {len(context.get('recent_interactions', []))} interactions récupérées")
        
        # Si pas de souvenirs, créer un contexte minimal mais présent
        # MAIS ne pas écraser les interactions existantes
        if not context.get("memories") or len(context.get("memories", [])) == 0:
            # Créer un souvenir de session actuelle pour forcer la présence de la mémoire
            try:
                self.memory.add_memory_from_interaction(
                    content=f"Session en cours: {message[:100]}",
                    category="session",
                    importance_score=0.3
                )
                # Re-récupérer le contexte
                context = self.memory.get_context(limit_traits=limit_traits, limit_memories=limit_memories, limit_interactions=limit_interactions)
                logger.debug("Souvenir de session créé pour activer la mémoire")
            except Exception as e:
                logger.warning(f"Impossible de créer un souvenir de session: {e}")
        
        # Chercher des mots-clés dans le message pour trouver des souvenirs pertinents
        keywords = self._extract_keywords(message)
        
        # Si des mots-clés trouvés, on pourrait chercher des souvenirs spécifiques
        # Pour l'instant, on utilise le contexte de base
        if keywords:
            logger.debug(f"Mots-clés extraits: {keywords}")
        
        return context
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrait les mots-clés d'un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Liste de mots-clés
        """
        # Mots vides à ignorer
        stop_words = {
            "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "mais", 
            "pour", "avec", "sans", "sur", "dans", "par", "est", "sont", "être", 
            "avoir", "faire", "peux", "peut", "veux", "veut", "tu", "je", "il", 
            "elle", "nous", "vous", "ils", "elles", "qui", "que", "quoi", "où", 
            "comment", "pourquoi", "quand", "comme", "très", "plus", "moins"
        }
        
        # Nettoyer et extraire les mots
        words = text.lower().replace("?", "").replace("!", "").replace(".", "").replace(",", "").split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return keywords[:5]  # Top 5 mots-clés
    
    def should_activate_memory(self, message: str) -> bool:
        """
        Détermine si la mémoire doit être activée pour ce message.
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si la mémoire doit être activée
        """
        # Toujours activer la mémoire pour l'instant
        # On pourrait ajouter une logique plus sophistiquée plus tard
        return True
    
    def enrich_context_with_memories(self, context: Dict[str, Any], message: str) -> Dict[str, Any]:
        """
        Enrichit le contexte avec des souvenirs pertinents basés sur le message.
        
        Args:
            context: Contexte de base
            message: Message de l'utilisateur
        
        Returns:
            Contexte enrichi
        """
        # Pour l'instant, on retourne le contexte tel quel
        # On pourrait implémenter une recherche sémantique plus tard
        return context


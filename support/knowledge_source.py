"""Interface pour les sources de connaissance."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class KnowledgeSource(ABC):
    """Interface abstraite pour une source de connaissance."""
    
    @abstractmethod
    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Interroge la source de connaissance.
        
        Args:
            question: Question à poser
            context: Contexte optionnel (traits, souvenirs, etc.)
        
        Returns:
            Réponse de la source de connaissance
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si la source de connaissance est disponible.
        
        Returns:
            True si disponible, False sinon
        """
        pass


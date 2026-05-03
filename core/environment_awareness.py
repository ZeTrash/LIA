"""Module de conscience environnementale pour LIA."""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Capability(Enum):
    """Capacités disponibles pour LIA."""
    MEMORY = "memory"
    GEMINI = "gemini"
    USER_INTERACTION = "user_interaction"
    LEARNING = "learning"
    DEBATE = "debate"


class EnvironmentAwareness:
    """Gère la conscience environnementale de LIA."""
    
    def __init__(self, memory_adapter=None, gemini_adapter=None):
        """
        Initialise la conscience environnementale.
        
        Args:
            memory_adapter: Adaptateur mémoire (optionnel)
            gemini_adapter: Adaptateur Gemini (optionnel)
        """
        self.memory = memory_adapter
        self.gemini = gemini_adapter
        self.capabilities = self._detect_capabilities()
        logger.info("EnvironmentAwareness initialisé")
    
    def _detect_capabilities(self) -> Dict[str, bool]:
        """
        Détecte les capacités disponibles.
        
        Returns:
            Dictionnaire des capacités disponibles
        """
        return {
            "memory": self.memory is not None,
            "gemini": self.gemini is not None,
            "user_interaction": True,  # Toujours disponible
            "learning": self.memory is not None,
            "debate": self.gemini is not None and self.memory is not None
        }
    
    def get_environment_description(self) -> str:
        """
        Retourne une description de l'environnement pour LIA.
        Version condensée pour économiser des tokens.
        
        Returns:
            Description de l'environnement
        """
        desc_parts = []
        
        desc_parts.append("=== MON ENVIRONNEMENT ===")
        
        if self.capabilities["memory"]:
            desc_parts.append("• MÉMOIRE : J'ai une mémoire persistante. Je peux stocker et récupérer mes souvenirs, ma personnalité et mes objectifs. Je peux solliciter cette mémoire à tout moment.")
        
        if self.capabilities["gemini"]:
            desc_parts.append("• GEMINI : J'ai accès à Gemini, une source de connaissances externes. Je peux poser des questions à Gemini, débattre avec lui, ou lui demander des informations. Je peux solliciter Gemini moi-même quand j'en ai besoin.")
        
        desc_parts.append("• UTILISATEUR : Je peux interagir avec un utilisateur, poser des questions, échanger et apprendre. Si je manque d'information pour répondre, je peux demander des clarifications à l'utilisateur directement dans ma réponse.")
        desc_parts.append("")
        desc_parts.append("Je suis autonome : je peux décider quand utiliser ma mémoire, quand solliciter Gemini, et quand demander des clarifications à l'utilisateur. Si je manque d'information, je pose une question à l'utilisateur au lieu d'inventer ou de générer des interactions fictives.")
        
        return "\n".join(desc_parts)
    
    def can_use(self, capability: Capability) -> bool:
        """
        Vérifie si une capacité est disponible.
        
        Args:
            capability: Capacité à vérifier
        
        Returns:
            True si la capacité est disponible
        """
        return self.capabilities.get(capability.value, False)
    
    def get_capabilities_summary(self) -> str:
        """
        Retourne un résumé court des capacités disponibles.
        
        Returns:
            Résumé des capacités
        """
        available = [cap.value for cap in Capability if self.can_use(cap)]
        return f"Capacités disponibles: {', '.join(available)}"



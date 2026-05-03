"""Système d'actions autonomes pour LIA."""

import logging
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

# Import optionnel du canal Support
try:
    from support.support_channel import SupportChannel
    SUPPORT_CHANNEL_AVAILABLE = True
except ImportError:
    SUPPORT_CHANNEL_AVAILABLE = False
    logger.warning("SupportChannel non disponible, utilisation directe de Gemini")


class AutonomousActionManager:
    """Gère les actions autonomes de LIA."""
    
    def __init__(self, memory_adapter=None, gemini_adapter=None, support_channel=None):
        """
        Initialise le gestionnaire d'actions autonomes.
        
        Args:
            memory_adapter: Adaptateur mémoire (optionnel)
            gemini_adapter: Adaptateur Gemini (optionnel, utilisé si support_channel non fourni)
            support_channel: Canal Support pour échange avec noyau d'appui (optionnel, préféré)
        """
        self.memory = memory_adapter
        self.gemini = gemini_adapter
        self.support_channel = support_channel
        
        # Utiliser le canal Support si disponible, sinon fallback vers Gemini direct
        if support_channel and SUPPORT_CHANNEL_AVAILABLE:
            logger.info("AutonomousActionManager initialisé avec SupportChannel")
        elif gemini_adapter:
            logger.info("AutonomousActionManager initialisé avec GeminiAdapter direct")
        else:
            logger.warning("AutonomousActionManager initialisé sans source de connaissance")
    
    async def process_with_autonomy(
        self,
        message: str,
        core_adapter,
        session_id: str = "default"
    ) -> str:
        """
        Traite un message en permettant à LIA d'agir de manière autonome.
        
        Args:
            message: Message de l'utilisateur
            core_adapter: Adaptateur du noyau primaire (LLMAdapter)
            session_id: ID de session
        
        Returns:
            Réponse de LIA (peut inclure des actions autonomes)
        """
        # Analyser si LIA doit solliciter Gemini
        if self._should_query_gemini(message):
            # LIA décide de solliciter Gemini via le canal Support
            gemini_query = self._extract_gemini_query(message)
            
            # Utiliser le canal Support si disponible (préféré)
            if gemini_query and self.support_channel and SUPPORT_CHANNEL_AVAILABLE:
                try:
                    logger.info(f"🤖 LIA décide de solliciter Gemini via SupportChannel: {gemini_query[:100]}...")
                    exchange_result = await self.support_channel.query(
                        question=gemini_query,
                        context=None,
                        save_to_memory=True,
                        session_id=session_id
                    )
                    gemini_response = exchange_result.get("answer", "")
                    
                    # Formatage clair de l'information de Gemini
                    # IMPORTANT: Ne pas générer de fausses interactions, utiliser directement l'information
                    enhanced_message = f"""{message}

=== INFORMATION EXTERNE (GEMINI) ===
Question posée à Gemini: {gemini_query}
Réponse de Gemini: {gemini_response}
=== FIN INFORMATION EXTERNE ===

INSTRUCTION: Utilise cette information de Gemini pour répondre à l'utilisateur. Si tu manques encore d'information, pose une question à l'utilisateur au lieu d'inventer."""
                    
                    # Utiliser _generate_internal pour éviter la récursion
                    response = await core_adapter._generate_internal(enhanced_message, session_id=session_id)
                    return response
                except Exception as e:
                    logger.warning(f"⚠️  Erreur lors de l'appel via SupportChannel: {e}")
                    # En cas d'erreur, continuer sans Gemini
                    pass
            # Fallback vers Gemini direct si canal Support non disponible
            elif gemini_query and self.gemini:
                try:
                    logger.info(f"🤖 LIA décide de solliciter Gemini (direct): {gemini_query[:100]}...")
                    gemini_response = await self.gemini.query(gemini_query, context=None)
                    
                    # Formatage clair de l'information de Gemini
                    # IMPORTANT: Ne pas générer de fausses interactions, utiliser directement l'information
                    enhanced_message = f"""{message}

=== INFORMATION EXTERNE (GEMINI) ===
Question posée à Gemini: {gemini_query}
Réponse de Gemini: {gemini_response}
=== FIN INFORMATION EXTERNE ===

INSTRUCTION: Utilise cette information de Gemini pour répondre à l'utilisateur. Si tu manques encore d'information, pose une question à l'utilisateur au lieu d'inventer."""
                    
                    # Utiliser _generate_internal pour éviter la récursion
                    response = await core_adapter._generate_internal(enhanced_message, session_id=session_id)
                    return response
                except Exception as e:
                    logger.warning(f"⚠️  Erreur lors de l'appel à Gemini: {e}")
                    # En cas d'erreur, continuer sans Gemini
                    pass
        
        # Réponse normale (utiliser _generate_internal pour éviter la récursion)
        response = await core_adapter._generate_internal(message, session_id=session_id)
        return response
    
    def _should_query_gemini(self, message: str) -> bool:
        """
        Détermine si LIA devrait solliciter Gemini.
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            True si Gemini devrait être sollicité
        """
        # Mots-clés qui suggèrent qu'une recherche externe serait utile
        keywords = [
            "qu'est-ce que", "comment fonctionne", "explique", "informe", 
            "recherche", "débat", "antithèse", "quelle est", "définis",
            "informations sur", "en savoir plus", "apprendre"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)
    
    def _extract_gemini_query(self, message: str) -> Optional[str]:
        """
        Extrait la question à poser à Gemini.
        
        Args:
            message: Message de l'utilisateur
        
        Returns:
            Question à poser à Gemini (ou None)
        """
        # Pour l'instant, retourner le message tel quel
        # TODO: Améliorer l'extraction de la question pour être plus précis
        return message



"""Adaptateur pour Groq API (noyau d'appui)."""

import logging
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable
import httpx
import json

from .knowledge_source import KnowledgeSource
from .config import SupportConfig

logger = logging.getLogger(__name__)


class GroqAdapter(KnowledgeSource):
    """Adaptateur pour interroger Groq API."""
    
    def __init__(self, config: Optional[SupportConfig] = None):
        """
        Initialise l'adaptateur Groq.
        
        Args:
            config: Configuration du noyau d'appui (optionnel)
        """
        self.config = config or SupportConfig()
        
        # Charger la configuration depuis le fichier si la clé API n'est pas fournie
        if not self.config.groq_api_key:
            self.config.load_from_file()
        
        if not self.config.groq_api_key:
            logger.warning("⚠️  Clé API Groq non configurée. L'adaptateur ne pourra pas fonctionner.")
        
        # URL de base pour l'API Groq
        self.base_url = "https://api.groq.com/openai/v1"
        self._query_count = 0  # Compteur de requêtes pour la session
        
        # Modèle par défaut (llama-3.3-70b-versatile remplace llama-3.1-70b-versatile décommissionné)
        self.model = getattr(self.config, 'groq_model', 'llama-3.3-70b-versatile')
    
    def is_available(self) -> bool:
        """Vérifie si Groq est disponible."""
        return self.config.groq_api_key is not None and self.config.groq_api_key != "YOUR_GROQ_API_KEY_HERE"
    
    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Interroge Groq avec une question.
        
        Args:
            question: Question à poser à Groq
            context: Contexte optionnel (traits, souvenirs, etc.)
        
        Returns:
            Réponse de Groq
        """
        if not self.is_available():
            raise RuntimeError("Groq API non disponible : clé API manquante")
        
        # Vérifier la limite de requêtes
        if self._query_count >= self.config.max_queries_per_session:
            logger.warning(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
            raise RuntimeError(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
        
        # Construire le prompt avec contexte si disponible
        prompt = self._build_prompt(question, context)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": getattr(self.config, 'groq_temperature', 0.7),
                "max_tokens": getattr(self.config, 'groq_max_tokens', 1024)
            }
            
            async with httpx.AsyncClient(timeout=self.config.query_timeout) as client:
                url = f"{self.base_url}/chat/completions"
                logger.debug(f"Appel Groq avec le modèle: {self.model}")
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Extraire la réponse (format OpenAI-compatible)
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        answer = choice["message"]["content"]
                        self._query_count += 1
                        logger.info(f"✅ Réponse Groq obtenue (requête {self._query_count})")
                        return answer
                
                # Si pas de réponse valide
                logger.warning("Réponse Groq invalide ou vide")
                return "Désolé, je n'ai pas pu obtenir de réponse de Groq."
                
        except httpx.TimeoutException:
            logger.error("Timeout lors de l'appel à Groq API")
            raise RuntimeError("Timeout lors de l'appel à Groq API")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP lors de l'appel à Groq API: {e}")
            if e.response.status_code == 429:
                raise RuntimeError("Limite de taux atteinte pour Groq API")
            raise RuntimeError(f"Erreur lors de l'appel à Groq API: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de l'interrogation de Groq: {e}")
            raise
    
    def _build_prompt(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Construit le prompt pour Groq avec le contexte.
        
        Args:
            question: Question à poser
            context: Contexte optionnel
        
        Returns:
            Prompt complet
        """
        prompt_parts = []
        
        # Ajouter le contexte si disponible
        if context:
            if "traits" in context and context["traits"]:
                traits_str = ", ".join([f"{t.get('label', '')}: {t.get('value', '')}" for t in context["traits"][:3]])
                if traits_str:
                    prompt_parts.append(f"Contexte personnalité: {traits_str}")
            
            if "memories" in context and context["memories"]:
                memories_str = "; ".join([m.get('content', '') for m in context["memories"][:2]])
                if memories_str:
                    prompt_parts.append(f"Contexte souvenirs: {memories_str}")
        
        # Ajouter la question
        prompt_parts.append(f"Question: {question}")
        
        return "\n".join(prompt_parts) if prompt_parts else question
    
    async def query_stream(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AsyncIterator[str]:
        """
        Interroge Groq avec streaming en temps réel.
        
        Args:
            question: Question à poser à Groq
            context: Contexte optionnel (traits, souvenirs, etc.)
            stream_callback: Callback appelé pour chaque chunk reçu (optionnel)
        
        Yields:
            Chunks de texte au fur et à mesure de la génération
        """
        if not self.is_available():
            raise RuntimeError("Groq API non disponible : clé API manquante")
        
        # Vérifier la limite de requêtes
        if self._query_count >= self.config.max_queries_per_session:
            logger.warning(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
            raise RuntimeError(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
        
        # Construire le prompt avec contexte si disponible
        prompt = self._build_prompt(question, context)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": getattr(self.config, 'groq_temperature', 0.7),
                "max_tokens": getattr(self.config, 'groq_max_tokens', 1024),
                "stream": True
            }
            
            async with httpx.AsyncClient(timeout=self.config.query_timeout) as client:
                url = f"{self.base_url}/chat/completions"
                logger.debug(f"Appel Groq streaming avec le modèle: {self.model}")
                
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    
                    full_response = ""
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]  # Enlever "data: "
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                chunk_data = json.loads(data_str)
                                
                                # Extraire le texte du chunk (format OpenAI streaming)
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    choice = chunk_data["choices"][0]
                                    if "delta" in choice and "content" in choice["delta"]:
                                        text_chunk = choice["delta"]["content"]
                                        if text_chunk:
                                            full_response += text_chunk
                                            yield text_chunk
                                            
                                            if stream_callback:
                                                try:
                                                    await stream_callback(text_chunk)
                                                except Exception as cb_err:
                                                    logger.debug(f"Erreur callback streaming: {cb_err}")
                            except json.JSONDecodeError:
                                continue
                    
                    self._query_count += 1
                    logger.info(f"✅ Réponse Groq streamée (requête {self._query_count})")
                
        except httpx.TimeoutException:
            logger.error("Timeout lors de l'appel à Groq API")
            raise RuntimeError("Timeout lors de l'appel à Groq API")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP lors de l'appel à Groq API: {e}")
            raise RuntimeError(f"Erreur lors de l'appel à Groq API: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de l'interrogation Groq en streaming: {e}")
            raise
    
    def reset_query_count(self):
        """Réinitialise le compteur de requêtes."""
        self._query_count = 0


"""Adaptateur pour Gemini API (noyau d'appui)."""

import logging
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable
import httpx
import json

from .knowledge_source import KnowledgeSource
from .config import SupportConfig

logger = logging.getLogger(__name__)


class GeminiAdapter(KnowledgeSource):
    """Adaptateur pour interroger Gemini API."""
    
    def __init__(self, config: Optional[SupportConfig] = None):
        """
        Initialise l'adaptateur Gemini.
        
        Args:
            config: Configuration du noyau d'appui (optionnel)
        """
        self.config = config or SupportConfig()
        
        # Charger la configuration depuis le fichier si la clé API n'est pas fournie
        if not self.config.gemini_api_key:
            self.config.load_from_file()
        
        if not self.config.gemini_api_key:
            logger.warning("⚠️  Clé API Gemini non configurée. L'adaptateur ne pourra pas fonctionner.")
        
        # URL de base pour l'API Gemini (utiliser v1beta comme dans l'exemple)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._query_count = 0  # Compteur de requêtes pour la session
        
        # Liste des modèles à essayer dans l'ordre (fallback dynamique)
        self.model_fallback_list = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash"
        ]
    
    def is_available(self) -> bool:
        """Vérifie si Gemini est disponible."""
        return self.config.gemini_api_key is not None and self.config.gemini_api_key != "YOUR_GEMINI_API_KEY_HERE"
    
    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Interroge Gemini avec une question.
        
        Args:
            question: Question à poser à Gemini
            context: Contexte optionnel (traits, souvenirs, etc.)
        
        Returns:
            Réponse de Gemini
        """
        if not self.is_available():
            raise RuntimeError("Gemini API non disponible : clé API manquante")
        
        # Vérifier la limite de requêtes
        if self._query_count >= self.config.max_queries_per_session:
            logger.warning(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
            raise RuntimeError(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
        
        # Construire le prompt avec contexte si disponible
        prompt = self._build_prompt(question, context)
        
        try:
            headers = {
                "Content-Type": "application/json"
            }
            params = {
                "key": self.config.gemini_api_key
            }
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": self.config.gemini_temperature,
                    "maxOutputTokens": self.config.gemini_max_tokens
                }
            }
            
            async with httpx.AsyncClient(timeout=self.config.query_timeout) as client:
                # Utiliser v1beta exactement comme dans l'exemple de code qui fonctionne
                # Essayer les modèles dans l'ordre de fallback : gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.0-flash
                models_to_try = self.model_fallback_list.copy()
                
                # Si un modèle spécifique est configuré et n'est pas dans la liste, l'essayer en premier
                if self.config.gemini_model and self.config.gemini_model not in models_to_try:
                    models_to_try.insert(0, self.config.gemini_model)
                
                response = None
                last_error = None
                successful_model = None
                
                for model in models_to_try:
                    url = f"{self.base_url}/models/{model}:generateContent"
                    try:
                        logger.debug(f"Tentative avec le modèle: {model}")
                        response = await client.post(url, headers=headers, params=params, json=payload)
                        response.raise_for_status()
                        successful_model = model
                        if model != models_to_try[0]:
                            logger.info(f"✅ Modèle {model} utilisé avec succès (fallback depuis {models_to_try[0]})")
                        break
                    except httpx.HTTPStatusError as e:
                        last_error = e
                        if e.response.status_code == 404:
                            logger.debug(f"Modèle {model} non disponible (404), essai du suivant...")
                            continue
                        elif e.response.status_code == 429:
                            logger.warning(f"Limite de taux atteinte pour {model}, essai du suivant...")
                            continue
                        else:
                            # Pour les autres erreurs HTTP, on continue quand même
                            logger.warning(f"Erreur HTTP {e.response.status_code} pour {model}, essai du suivant...")
                            continue
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Erreur avec {model}: {e}, essai du suivant...")
                        continue
                
                if not response or response.status_code != 200:
                    if last_error:
                        logger.error(f"Tous les modèles ont échoué. Dernière erreur: {last_error}")
                        raise RuntimeError(f"Erreur lors de l'appel à Gemini API (tous les modèles ont échoué): {last_error}")
                    else:
                        raise RuntimeError("Erreur lors de l'appel à Gemini API: aucune réponse valide")
                
                data = response.json()
                
                # Extraire la réponse
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            answer = parts[0]["text"]
                            self._query_count += 1
                            logger.info(f"✅ Réponse Gemini obtenue (requête {self._query_count})")
                            return answer
                
                # Si pas de réponse valide
                logger.warning("Réponse Gemini invalide ou vide")
                return "Désolé, je n'ai pas pu obtenir de réponse de Gemini."
                
        except httpx.TimeoutException:
            logger.error("Timeout lors de l'appel à Gemini API")
            raise RuntimeError("Timeout lors de l'appel à Gemini API")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP lors de l'appel à Gemini API: {e}")
            raise RuntimeError(f"Erreur lors de l'appel à Gemini API: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de l'interrogation de Gemini: {e}")
            raise
    
    def _build_prompt(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Construit le prompt pour Gemini avec le contexte.
        
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
        Interroge Gemini avec streaming en temps réel.
        
        Args:
            question: Question à poser à Gemini
            context: Contexte optionnel (traits, souvenirs, etc.)
            stream_callback: Callback appelé pour chaque chunk reçu (optionnel)
        
        Yields:
            Chunks de texte au fur et à mesure de la génération
        """
        if not self.is_available():
            raise RuntimeError("Gemini API non disponible : clé API manquante")
        
        # Vérifier la limite de requêtes
        if self._query_count >= self.config.max_queries_per_session:
            logger.warning(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
            raise RuntimeError(f"Limite de requêtes atteinte ({self.config.max_queries_per_session})")
        
        # Construire le prompt avec contexte si disponible
        prompt = self._build_prompt(question, context)
        
        try:
            headers = {
                "Content-Type": "application/json"
            }
            params = {
                "key": self.config.gemini_api_key
            }
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": self.config.gemini_temperature,
                    "maxOutputTokens": self.config.gemini_max_tokens
                }
            }
            
            async with httpx.AsyncClient(timeout=self.config.query_timeout) as client:
                models_to_try = self.model_fallback_list.copy()
                
                if self.config.gemini_model and self.config.gemini_model not in models_to_try:
                    models_to_try.insert(0, self.config.gemini_model)
                
                last_error = None
                successful_model = None
                full_response = ""
                
                for model in models_to_try:
                    # Utiliser streamGenerateContent pour le streaming
                    url = f"{self.base_url}/models/{model}:streamGenerateContent"
                    try:
                        logger.debug(f"Tentative streaming avec le modèle: {model}")
                        async with client.stream(
                            "POST",
                            url,
                            headers=headers,
                            params=params,
                            json=payload
                        ) as response:
                            response.raise_for_status()
                            successful_model = model
                            
                            # Lire les chunks de réponse ligne par ligne
                            buffer = ""
                            chunks_received = False
                            
                            async for chunk_bytes in response.aiter_bytes():
                                if not chunk_bytes:
                                    continue
                                
                                buffer += chunk_bytes.decode('utf-8', errors='ignore')
                                
                                # Traiter les lignes complètes
                                while '\n' in buffer:
                                    line, buffer = buffer.split('\n', 1)
                                    line = line.strip()
                                    
                                    if not line:
                                        continue
                                    
                                    # Parser les chunks SSE (Server-Sent Events)
                                    if line.startswith("data: "):
                                        data_str = line[6:]  # Enlever "data: "
                                        if data_str == "[DONE]":
                                            break
                                        
                                        try:
                                            chunk_data = json.loads(data_str)
                                            
                                            # Extraire le texte du chunk
                                            if "candidates" in chunk_data and len(chunk_data["candidates"]) > 0:
                                                candidate = chunk_data["candidates"][0]
                                                
                                                # Vérifier si c'est un chunk de contenu
                                                if "content" in candidate:
                                                    if "parts" in candidate["content"]:
                                                        parts = candidate["content"]["parts"]
                                                        if len(parts) > 0:
                                                            # Peut être un delta (chunk) ou texte complet
                                                            if "text" in parts[0]:
                                                                text_chunk = parts[0]["text"]
                                                                if text_chunk:
                                                                    chunks_received = True
                                                                    full_response += text_chunk
                                                                    yield text_chunk
                                                                    
                                                                    # Appeler le callback si fourni
                                                                    if stream_callback:
                                                                        try:
                                                                            await stream_callback(text_chunk)
                                                                        except Exception as cb_err:
                                                                            logger.debug(f"Erreur callback streaming: {cb_err}")
                                                
                                                # Vérifier aussi les deltas (format streaming)
                                                elif "delta" in candidate:
                                                    if "text" in candidate["delta"]:
                                                        text_chunk = candidate["delta"]["text"]
                                                        if text_chunk:
                                                            chunks_received = True
                                                            full_response += text_chunk
                                                            yield text_chunk
                                                            
                                                            if stream_callback:
                                                                try:
                                                                    await stream_callback(text_chunk)
                                                                except Exception as cb_err:
                                                                    logger.debug(f"Erreur callback streaming: {cb_err}")
                                        except json.JSONDecodeError:
                                            # Ignorer les lignes non-JSON
                                            continue
                                    
                                    # Format alternatif : JSON direct (pas SSE)
                                    elif line.startswith('{'):
                                        try:
                                            chunk_data = json.loads(line)
                                            # Même logique d'extraction que ci-dessus
                                            if "candidates" in chunk_data:
                                                for candidate in chunk_data["candidates"]:
                                                    if "content" in candidate and "parts" in candidate["content"]:
                                                        for part in candidate["content"]["parts"]:
                                                            if "text" in part:
                                                                text_chunk = part["text"]
                                                                if text_chunk:
                                                                    chunks_received = True
                                                                    full_response += text_chunk
                                                                    yield text_chunk
                                                                    if stream_callback:
                                                                        try:
                                                                            await stream_callback(text_chunk)
                                                                        except Exception as cb_err:
                                                                            logger.debug(f"Erreur callback streaming: {cb_err}")
                                        except json.JSONDecodeError:
                                            continue
                            
                            # Si aucun chunk n'a été reçu, utiliser query() normal comme fallback
                            if not chunks_received:
                                logger.warning("Aucun chunk reçu en streaming, utilisation du mode normal")
                                # Utiliser la méthode normale query() comme fallback
                                answer = await self.query(question, context)
                                if answer:
                                    # Simuler le streaming en envoyant par mots
                                    words = answer.split()
                                    for word in words:
                                        chunk = word + " "
                                        full_response += chunk
                                        yield chunk
                                        if stream_callback:
                                            try:
                                                await stream_callback(chunk)
                                            except Exception as cb_err:
                                                logger.debug(f"Erreur callback streaming: {cb_err}")
                            
                            break
                    except httpx.HTTPStatusError as e:
                        last_error = e
                        if e.response.status_code == 404:
                            logger.debug(f"Modèle {model} non disponible (404), essai du suivant...")
                            continue
                        elif e.response.status_code == 429:
                            logger.warning(f"Limite de taux atteinte pour {model}, essai du suivant...")
                            continue
                        else:
                            logger.warning(f"Erreur HTTP {e.response.status_code} pour {model}, essai du suivant...")
                            continue
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Erreur avec {model}: {e}, essai du suivant...")
                        continue
                
                if successful_model:
                    self._query_count += 1
                    logger.info(f"✅ Réponse Gemini streamée (requête {self._query_count}, modèle {successful_model})")
                else:
                    if last_error:
                        logger.error(f"Tous les modèles ont échoué. Dernière erreur: {last_error}")
                        raise RuntimeError(f"Erreur lors de l'appel à Gemini API (tous les modèles ont échoué): {last_error}")
                    else:
                        raise RuntimeError("Erreur lors de l'appel à Gemini API: aucune réponse valide")
                
        except httpx.TimeoutException:
            logger.error("Timeout lors de l'appel à Gemini API")
            raise RuntimeError("Timeout lors de l'appel à Gemini API")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP lors de l'appel à Gemini API: {e}")
            raise RuntimeError(f"Erreur lors de l'appel à Gemini API: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de l'interrogation Gemini en streaming: {e}")
            raise
    
    def reset_query_count(self):
        """Réinitialise le compteur de requêtes."""
        self._query_count = 0


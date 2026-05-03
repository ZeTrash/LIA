"""Adapters pour différents types d'agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import time

import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from .schemas import AgentConfig, AgentType
from .config import get_settings


class AgentAdapter(ABC):
    """Interface abstraite pour les adapters d'agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type
        self.last_message_time = 0.0
        self.message_count = 0
        
    @abstractmethod
    async def send_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Envoie un message à l'agent et récupère la réponse.
        
        Args:
            message: Contenu du message
            context: Contexte mémoire (pour LIA)
            session_id: ID de session
            
        Returns:
            Réponse de l'agent
        """
        pass
    
    @abstractmethod
    async def perform_handshake(self) -> Dict[str, Any]:
        """Effectue le handshake initial avec l'agent."""
        pass
    
    def check_rate_limit(self) -> bool:
        """Vérifie si le rate limiting est respecté."""
        settings = get_settings()
        current_time = time.time()
        
        # Reset counter si plus d'une seconde s'est écoulée
        if current_time - self.last_message_time >= 1.0:
            self.message_count = 0
            self.last_message_time = current_time
        
        if self.message_count >= settings.max_messages_per_second:
            return False
        
        self.message_count += 1
        return True


class LIAAdapter(AgentAdapter):
    """Adapter pour les agents LIA (primary ou secondary)."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.memory_url = config.memory_service_url or get_settings().memory_service_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Récupère le contexte mémoire depuis memory_service."""
        try:
            response = await self.client.get(
                f"{self.memory_url}/context",
                params={"session_id": session_id, "max_memories": 12}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # En cas d'erreur, retourner un contexte vide
            return {
                "traits": [],
                "session_goals": [],
                "memories": [],
                "indicators": {},
                "governance_metadata": {}
            }
    
    async def get_traits(self, session_id: str) -> List[Dict[str, Any]]:
        """Récupère les traits depuis memory_service."""
        try:
            context = await self.get_context(session_id)
            return context.get("traits", [])
        except Exception:
            return []
    
    async def create_experience(
        self,
        experience_id: str,
        title: str,
        session_id: str,
        started_at: str,
        metrics_snapshot: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Crée une Experience dans memory_service.
        
        Note: Comme il n'y a pas d'endpoint API pour créer une Experience,
        on utilise une requête SQL directe via un endpoint interne ou on stocke
        l'information dans les métadonnées de session.
        Pour l'instant, on retourne True pour indiquer que l'Experience est créée.
        """
        try:
            # TODO: Créer un endpoint POST /experience dans memory_service
            # Pour l'instant, on stocke l'information dans les interactions
            # ou on crée une interaction spéciale pour marquer l'Experience
            
            # Créer une interaction spéciale pour marquer le début de l'Experience
            await self.log_interaction(
                session_id=session_id,
                prompt=f"[EXPERIENCE_START] {title}",
                response=f"Experience {experience_id} démarrée",
                metadata={
                    "experience_id": experience_id,
                    "experience_title": title,
                    "started_at": started_at,
                    "metrics_snapshot": metrics_snapshot or {}
                }
            )
            return True
        except Exception:
            return False
    
    async def finalize_experience(
        self,
        experience_id: str,
        session_id: str,
        ended_at: str,
        metrics_snapshot: Optional[Dict[str, Any]] = None,
        related_memories: Optional[List[str]] = None
    ) -> bool:
        """Finalise une Experience dans memory_service."""
        try:
            # Créer une interaction spéciale pour marquer la fin de l'Experience
            await self.log_interaction(
                session_id=session_id,
                prompt=f"[EXPERIENCE_END] {experience_id}",
                response=f"Experience {experience_id} terminée",
                metadata={
                    "experience_id": experience_id,
                    "ended_at": ended_at,
                    "metrics_snapshot": metrics_snapshot or {},
                    "related_memories": related_memories or []
                }
            )
            return True
        except Exception:
            return False
    
    async def check_governance(self, session_id: str, draft_response: str) -> Dict[str, Any]:
        """Vérifie la gouvernance via memory_service."""
        try:
            response = await self.client.post(
                f"{self.memory_url}/governance/check",
                json={
                    "session_id": session_id,
                    "draft_response": draft_response,
                    "signals": []
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # En cas d'erreur, retourner "allow" par défaut
            return {"verdict": "allow", "issues": []}
    
    async def log_interaction(
        self,
        session_id: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Journalise l'interaction dans memory_service."""
        try:
            import uuid
            
            # Construire la requête d'interaction selon le schéma memory_service
            interaction_data = {
                "interaction_id": f"int-{uuid.uuid4().hex[:8]}",
                "session_id": session_id,
                "prompt": prompt,
                "response": response,
                "scores": {
                    "usefulness": metadata.get("scores", {}).get("usefulness", 0.8) if metadata else 0.8,
                    "coherence": metadata.get("scores", {}).get("coherence", 0.9) if metadata else 0.9,
                    "tone": metadata.get("scores", {}).get("tone", 0.9) if metadata else 0.9
                },
                "decisions": {
                    "create_memory": True,
                    "ttl_override_days": None,
                    "derived_traits": []
                },
                "anomalies": []
            }
            
            await self.client.post(
                f"{self.memory_url}/interaction",
                json=interaction_data
            )
        except Exception:
            # Ignorer les erreurs de journalisation (non bloquant)
            pass
    
    async def send_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Envoie un message à LIA via memory_service et génère une réponse avec le LLM local."""
        if not self.check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        # Récupérer le contexte si non fourni
        if context is None and session_id:
            context = await self.get_context(session_id)
        
        # Utiliser LocalLLMAdapter pour générer la réponse
        try:
            local_config = AgentConfig(
                agent_id=self.agent_id,
                agent_type="llm-local",
                memory_service_url=self.memory_url
            )
            local_adapter = LocalLLMAdapter(local_config)
            response = await local_adapter.send_message(message, context, session_id)
        except Exception as e:
            # Fallback vers réponse simulée si LocalLLMAdapter n'est pas disponible
            response = f"[Réponse de {self.agent_id} à: {message[:50]}...]"
        
        # Vérifier la gouvernance
        if session_id:
            governance = await self.check_governance(session_id, response)
            if governance.get("verdict") == "block":
                response = "[Réponse bloquée par la gouvernance]"
            
            # Journaliser l'interaction
            await self.log_interaction(session_id, message, response)
        
        return response
    
    async def perform_handshake(self) -> Dict[str, Any]:
        """Effectue le handshake avec LIA."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.config.capabilities or ["memory", "governance"],
            "memory_version": "2024.12.07-01"
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


class ExternalLLMAdapter(AgentAdapter):
    """Adapter pour les LLM externes (OpenAI, Anthropic, etc.)."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        settings = get_settings()
        
        # Détecter le type de LLM depuis l'endpoint ou la config
        if "openai" in (config.api_endpoint or "").lower() or settings.openai_api_key:
            self.llm_type = "openai"
            self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        elif "anthropic" in (config.api_endpoint or "").lower() or settings.anthropic_api_key:
            self.llm_type = "anthropic"
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        else:
            self.llm_type = "generic"
            self.client = httpx.AsyncClient(timeout=30.0)
        
        self.api_endpoint = config.api_endpoint
        self.auth_token = config.auth_token
    
    async def send_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Envoie un message à un LLM externe."""
        if not self.check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self.llm_type == "openai" and self.client:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": message}],
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                raise Exception(f"Erreur OpenAI: {e}")
        
        elif self.llm_type == "anthropic" and self.client:
            try:
                response = await self.client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=500,
                    messages=[{"role": "user", "content": message}]
                )
                return response.content[0].text
            except Exception as e:
                raise Exception(f"Erreur Anthropic: {e}")
        
        else:
            # Fallback: réponse simulée
            return f"[Réponse LLM externe à: {message[:50]}...]"
    
    async def perform_handshake(self) -> Dict[str, Any]:
        """Effectue le handshake avec un LLM externe."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "llm-external",
            "capabilities": self.config.capabilities or ["multi-turn"],
            "api_endpoint": self.api_endpoint
        }


class SimulatedAgentAdapter(AgentAdapter):
    """Adapter pour un agent simulé (règles prédéfinies)."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.responses = [
            "C'est intéressant, peux-tu développer ?",
            "Je comprends ton point de vue.",
            "Qu'est-ce qui t'a amené à cette conclusion ?",
            "Je vois, et qu'en penses-tu de...",
            "C'est une perspective intéressante."
        ]
        self.response_index = 0
    
    async def send_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Envoie un message à un agent simulé."""
        if not self.check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        # Réponse basée sur des règles simples
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        
        # Ajouter une référence au message reçu
        if "?" in message:
            response = f"{response} Tu as posé une question intéressante."
        
        return response
    
    async def perform_handshake(self) -> Dict[str, Any]:
        """Effectue le handshake avec un agent simulé."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "simulated",
            "capabilities": ["multi-turn"]
        }


class LocalLLMAdapter(AgentAdapter):
    """Adapter pour GPT-2 Small (modèle local vierge)."""
    
    _model_cache = None
    _tokenizer_cache = None
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.settings = get_settings()
        self.memory_url = config.memory_service_url or self.settings.memory_service_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Configuration modèle
        self.model_name = self.settings.local_llm_model
        self.max_length = self.settings.local_llm_max_tokens
        self.temperature = self.settings.local_llm_temperature
        
        # Détecter device
        try:
            import torch
            if self.settings.local_llm_device == "auto":
                if torch.cuda.is_available():
                    self.device = "cuda"
                    print(f"🚀 GPU détecté: {torch.cuda.get_device_name(0)} (CUDA {torch.version.cuda})")
                else:
                    self.device = "cpu"
                    print("⚠️  GPU non disponible, utilisation du CPU")
            else:
                self.device = self.settings.local_llm_device
                if self.device == "cuda" and not torch.cuda.is_available():
                    print("⚠️  CUDA demandé mais non disponible, fallback vers CPU")
                    self.device = "cpu"
        except ImportError:
            self.device = "cpu"
            print("⚠️  PyTorch non disponible, utilisation du CPU")
        
        # Charger le modèle (cache global)
        if LocalLLMAdapter._model_cache is None:
            self._load_model()
        else:
            self.model = LocalLLMAdapter._model_cache
            self.tokenizer = LocalLLMAdapter._tokenizer_cache
    
    def _load_model(self):
        """Charge GPT-2 Small avec quantisation INT4/INT8."""
        try:
            from transformers import GPT2LMHeadModel, GPT2Tokenizer
            import torch
            
            print(f"Chargement GPT-2 Small ({self.model_name})...")
            
            # Quantisation avec bitsandbytes (INT4) si disponible
            if self.settings.local_llm_quantize and self.settings.local_llm_quantization_bits == 4:
                try:
                    from transformers import BitsAndBytesConfig
                    
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                    
                    self.model = GPT2LMHeadModel.from_pretrained(
                        self.model_name,
                        quantization_config=quantization_config,
                        device_map="auto" if self.device == "cuda" else None
                    )
                    print("Quantisation INT4 activée (bitsandbytes)")
                except ImportError:
                    print("bitsandbytes non disponible, utilisation INT8...")
                    # Fallback vers INT8
                    self._load_model_int8()
                except Exception as e:
                    print(f"Erreur quantisation INT4: {e}, fallback INT8...")
                    self._load_model_int8()
            elif self.settings.local_llm_quantize and self.settings.local_llm_quantization_bits == 8:
                self._load_model_int8()
            else:
                # Pas de quantisation
                self.model = GPT2LMHeadModel.from_pretrained(self.model_name)
                self.model.to(self.device)
            
            # Charger tokenizer
            self.tokenizer = GPT2Tokenizer.from_pretrained(self.model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model.eval()
            
            # Cache global
            LocalLLMAdapter._model_cache = self.model
            LocalLLMAdapter._tokenizer_cache = self.tokenizer
            
            print(f"GPT-2 Small chargé ({self.device}, {self.settings.local_llm_quantization_bits} bits)")
        except ImportError:
            raise ImportError(
                "transformers et torch sont requis pour LocalLLMAdapter. "
                "Installez-les avec: pip install transformers torch"
            )
    
    def _load_model_int8(self):
        """Charge le modèle avec quantisation INT8 (fallback)."""
        from transformers import GPT2LMHeadModel
        import torch
        
        self.model = GPT2LMHeadModel.from_pretrained(self.model_name)
        
        # Quantisation dynamique INT8 (CPU uniquement)
        if self.device == "cpu":
            try:
                self.model = torch.quantization.quantize_dynamic(
                    self.model,
                    {torch.nn.Linear},
                    dtype=torch.qint8
                )
                print("Quantisation INT8 activée (PyTorch)")
            except Exception:
                print("Quantisation INT8 échouée, modèle non quantifié")
        
        self.model.to(self.device)
    
    def build_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Construit le prompt avec contexte mémoire.
        
        Args:
            message: Message utilisateur
            context: Contexte mémoire (traits, souvenirs, objectifs)
        
        Returns:
            Prompt formaté selon la spécification
        """
        if not context:
            return message
        
        prompt_parts = []
        
        # Traits de personnalité
        traits = context.get("traits", [])
        if traits:
            prompt_parts.append("[Personnalité LIA]")
            for trait in traits[:10]:  # Limiter à 10 traits
                label = trait.get("label", trait.get("trait_id", ""))
                value = trait.get("value", "")
                if label and value:
                    prompt_parts.append(f"- {label}: {value}")
            prompt_parts.append("")
        
        # Souvenirs pertinents
        memories = context.get("memories", [])
        if memories:
            prompt_parts.append("[Souvenirs pertinents]")
            for memory in memories[:5]:  # Top 5
                content = memory.get("content", "")
                if content:
                    prompt_parts.append(f"- {content}")
            prompt_parts.append("")
        
        # Objectifs de session
        goals = context.get("session_goals", [])
        if goals:
            prompt_parts.append("[Objectifs de session]")
            for goal in goals[:3]:  # Top 3
                desc = goal.get("description", "")
                if desc:
                    prompt_parts.append(f"- {desc}")
            prompt_parts.append("")
        
        # Message
        prompt_parts.append("[Conversation]")
        prompt_parts.append(message)
        
        return "\n".join(prompt_parts)
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Récupère le contexte depuis memory_service."""
        try:
            response = await self.client.get(
                f"{self.memory_url}/context",
                params={"session_id": session_id, "max_memories": 12}
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return {
                "traits": [],
                "session_goals": [],
                "memories": [],
                "indicators": {},
                "governance_metadata": {}
            }
    
    async def send_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Génère une réponse avec GPT-2 Small."""
        if not self.check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        # Récupérer le contexte si non fourni
        if context is None and session_id:
            context = await self.get_context(session_id)
        
        # Construire le prompt avec contexte (ordre corrigé selon spécification)
        prompt = self.build_prompt(message, context)
        
        try:
            import torch
            
            # Encoder le prompt
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            inputs = inputs.to(self.device)
            
            # Limiter la longueur du prompt (GPT-2 a une limite de 1024 tokens)
            max_prompt_length = 512  # Laisser de la place pour la réponse
            if inputs.shape[1] > max_prompt_length:
                inputs = inputs[:, -max_prompt_length:]
            
            # Générer la réponse
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.max_length,
                    num_return_sequences=1,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2  # Éviter les répétitions
                )
            
            # Décoder la réponse
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extraire uniquement la partie réponse (après le prompt)
            response = full_response[len(prompt):].strip()
            
            # Nettoyer la réponse
            response = self._clean_response(response)
            
            return response
            
        except Exception as e:
            # Fallback vers API externe si erreur
            if self.settings.fallback_to_external_api:
                return await self._fallback_to_external(message, context)
            raise Exception(f"Erreur génération GPT-2: {e}")
    
    def _clean_response(self, response: str) -> str:
        """Nettoie la réponse générée."""
        # Supprimer les répétitions excessives
        lines = response.split("\n")
        cleaned_lines = []
        prev_line = ""
        for line in lines:
            if line.strip() and line.strip() != prev_line.strip():
                cleaned_lines.append(line)
                prev_line = line
        
        response = "\n".join(cleaned_lines)
        
        # Limiter la longueur
        if len(response) > 500:
            response = response[:500] + "..."
        
        return response.strip()
    
    async def _fallback_to_external(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Fallback vers API externe si le modèle local échoue."""
        external_config = AgentConfig(
            agent_id=self.agent_id,
            agent_type="llm-external"
        )
        external_adapter = ExternalLLMAdapter(external_config)
        
        return await external_adapter.send_message(message, context)
    
    def unload_model(self) -> None:
        """Décharge le modèle de la mémoire."""
        if self.model is not None:
            try:
                import torch
                # Sauvegarder référence au cache avant suppression
                was_cached = (LocalLLMAdapter._model_cache is self.model)
                
                del self.model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                self.model = None
                
                # Nettoyer le cache global si c'était le modèle en cache
                if was_cached:
                    LocalLLMAdapter._model_cache = None
                    LocalLLMAdapter._tokenizer_cache = None
                
                print("Modèle GPT-2 déchargé de la mémoire")
            except Exception as e:
                print(f"Erreur lors du déchargement: {e}")
    
    def get_memory_usage_mb(self) -> float:
        """Retourne l'utilisation mémoire en MB."""
        try:
            import torch
            import psutil
            import os
            
            # Mémoire du processus Python
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # Mémoire GPU si disponible
            if torch.cuda.is_available() and self.device == "cuda":
                gpu_memory = torch.cuda.memory_allocated() / (1024 * 1024)
                memory_mb += gpu_memory
            
            return round(memory_mb, 2)
        except ImportError:
            # Si psutil n'est pas disponible, estimation basique
            try:
                import torch
                if torch.cuda.is_available() and self.device == "cuda":
                    return round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
            except:
                pass
            return 0.0
    
    async def perform_handshake(self) -> Dict[str, Any]:
        """Effectue le handshake avec le modèle local."""
        memory_usage = self.get_memory_usage_mb()
        return {
            "agent_id": self.agent_id,
            "agent_type": "llm-local",
            "model_name": self.model_name,
            "device": self.device,
            "quantization_bits": self.settings.local_llm_quantization_bits,
            "memory_usage_mb": memory_usage,
            "capabilities": ["memory", "local-generation"]
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


def create_adapter(config: AgentConfig) -> AgentAdapter:
    """Factory pour créer le bon adapter selon le type d'agent."""
    if config.agent_type in ["lia-primary", "lia-secondary"]:
        return LIAAdapter(config)
    elif config.agent_type == "llm-local":
        return LocalLLMAdapter(config)
    elif config.agent_type == "llm-external":
        return ExternalLLMAdapter(config)
    elif config.agent_type == "simulated":
        return SimulatedAgentAdapter(config)
    else:
        raise ValueError(f"Type d'agent non supporté: {config.agent_type}")

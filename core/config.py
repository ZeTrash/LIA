"""Configuration du noyau primaire."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class CoreConfig:
    """Configuration du noyau primaire."""
    
    # Modèle
    model_name: str = "Qwen/Qwen2.5-72B-Instruct"  # LangBrain par défaut (doc V2)
    model_path: Optional[str] = None  # Chemin local vers le modèle (si None, télécharge depuis HuggingFace)
    local_models_dir: str = "models"  # Dossier pour stocker les modèles localement
    model_cache_dir: str = "models/hf_cache"  # Cache persistant HuggingFace/vLLM (évite les re-téléchargements)
    device: str = "auto"  # "auto", "cpu", "cuda"
    
    # Backend de chargement
    backend: str = "auto"  # "auto", "gguf", "transformers", "vllm"
    use_gguf: bool = True  # Utiliser GGUF + llama.cpp sur CPU (recommandé pour CPU-only)
    gguf_model_path: Optional[str] = "models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"  # Si None, cherche automatiquement dans le dossier models
    
    # vLLM (serving local via moteur Python)
    vllm_dtype: str = "auto"  # "auto", "float16", "bfloat16"
    vllm_max_model_len: int = 32768
    vllm_gpu_memory_utilization: float = 0.75
    router_gpu_memory_utilization: float = 0.08
    router_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    lang_model: Optional[str] = "Qwen/Qwen2.5-72B-Instruct"
    code_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    code_gpu_memory_utilization: float = 0.2
    vision_model: str = "meta-llama/Llama-3.2-11B-Vision-Instruct"
    audio_stt_model: str = "openai/whisper-large-v3"
    audio_tts_model: str = "hexgrad/Kokoro-82M"
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    
    # Génération
    max_length: int = 15360  # V2: budget par défaut aligné architecture MI300X
    temperature: float = 0.8  # Augmenté pour favoriser la créativité et l'expression de l'identité
    top_p: float = 0.95  # Augmenté pour plus de diversité dans les réponses
    top_k: int = 50  # Standard pour Qwen
    repetition_penalty: float = 1.2  # Ajusté pour éviter répétitions mais permettre développement de l'identité
    
    # Quantisation
    quantize: bool = True
    quantization_bits: int = 4  # 4 ou 8
    
    # Limites
    max_prompt_length: int = 2048*16  # Qwen supporte jusqu'à 32K tokens, on limite à 2048 pour commencer
    
    # Contrôle
    enable_auto_calibration: bool = True  # LIA peut modifier ces paramètres
    enable_neural_router: bool = False  # Active le NeuralRouter MVP (routing d'intention)
    enable_real_brain_routing: bool = True  # Utilise le router_model pour classifier les intents
    router_min_confidence: float = 0.3  # Seuil minimum avant fallback pattern/heuristique
    # Autonomie (V2): mode d'orchestration avant génération
    # - "menu": boucle historique (menu -> choix -> exécution -> repeat)
    # - "auto_with_audit": planification+exécution autonome, avec traces compatibles
    # - "full_auto": identique à auto_with_audit côté runtime (réservé pour futures optimisations)
    autonomy_mode: str = "auto_with_audit"
    router_confidence_threshold: float = 0.70
    max_router_replans: int = 2
    enable_menu_fallback: bool = True
    autonomy_min_plan_confidence: float = 0.55
    autonomy_require_execution_success: bool = True
    autonomy_max_replans: int = 1
    autonomy_prompt_min_confidence: float = 0.55
    autonomy_max_prompt_rebuilds: int = 1
    max_tool_calls: int = 5
    enable_pattern_brain_remote: bool = True  # Utilise le service HTTP pattern_brain si disponible
    enable_pattern_brain_local_fallback: bool = True  # Fallback local via LLM principal
    enable_code_brain: bool = True
    enable_vision_brain: bool = True
    enable_audio_brain: bool = False
    enable_identity_brain: bool = True
    enable_self_improvement: bool = True
    sandbox_timeout_seconds: int = 60
    max_self_modifications_per_session: int = 3
    require_human_approval_for_self_mod: bool = False
    system_log_path: str = "logs/lia_system_events.jsonl"
    
    def to_dict(self) -> dict:
        """Convertit la configuration en dictionnaire."""
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "local_models_dir": self.local_models_dir,
            "model_cache_dir": self.model_cache_dir,
            "device": self.device,
            "backend": self.backend,
            "use_gguf": self.use_gguf,
            "gguf_model_path": self.gguf_model_path,
            "vllm_dtype": self.vllm_dtype,
            "vllm_max_model_len": self.vllm_max_model_len,
            "vllm_gpu_memory_utilization": self.vllm_gpu_memory_utilization,
            "router_gpu_memory_utilization": self.router_gpu_memory_utilization,
            "router_model": self.router_model,
            "lang_model": self.lang_model,
            "code_model": self.code_model,
            "code_gpu_memory_utilization": self.code_gpu_memory_utilization,
            "vision_model": self.vision_model,
            "audio_stt_model": self.audio_stt_model,
            "audio_tts_model": self.audio_tts_model,
            "embedding_model": self.embedding_model,
            "max_length": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "quantize": self.quantize,
            "quantization_bits": self.quantization_bits,
            "max_prompt_length": self.max_prompt_length,
            "enable_auto_calibration": self.enable_auto_calibration,
            "enable_neural_router": self.enable_neural_router,
            "enable_real_brain_routing": self.enable_real_brain_routing,
            "router_min_confidence": self.router_min_confidence,
            "autonomy_mode": self.autonomy_mode,
            "router_confidence_threshold": self.router_confidence_threshold,
            "max_router_replans": self.max_router_replans,
            "enable_menu_fallback": self.enable_menu_fallback,
            "max_tool_calls": self.max_tool_calls,
            "enable_pattern_brain_remote": self.enable_pattern_brain_remote,
            "enable_pattern_brain_local_fallback": self.enable_pattern_brain_local_fallback,
            "enable_code_brain": self.enable_code_brain,
            "enable_vision_brain": self.enable_vision_brain,
            "enable_audio_brain": self.enable_audio_brain,
            "enable_identity_brain": self.enable_identity_brain,
            "enable_self_improvement": self.enable_self_improvement,
            "sandbox_timeout_seconds": self.sandbox_timeout_seconds,
            "max_self_modifications_per_session": self.max_self_modifications_per_session,
            "require_human_approval_for_self_mod": self.require_human_approval_for_self_mod,
            "system_log_path": self.system_log_path,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CoreConfig":
        """Crée une configuration depuis un dictionnaire."""
        return cls(**data)
    
    def update(self, **kwargs) -> None:
        """Met à jour la configuration."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


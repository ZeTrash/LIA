"""Configuration du noyau primaire."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class CoreConfig:
    """Configuration du noyau primaire."""
    
    # Modèle
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"  # Modèle par défaut : Qwen 2.5 1.5B Instruct
    model_path: Optional[str] = None  # Chemin local vers le modèle (si None, télécharge depuis HuggingFace)
    local_models_dir: str = "models"  # Dossier pour stocker les modèles localement
    device: str = "auto"  # "auto", "cpu", "cuda"
    
    # Backend de chargement
    use_gguf: bool = True  # Utiliser GGUF + llama.cpp sur CPU (recommandé pour CPU-only)
    gguf_model_path: Optional[str] = "models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"  # Si None, cherche automatiquement dans le dossier models
    
    # Génération
    max_length: int = 15360  # Qwen supporte jusqu'à 32K tokens, on limite à 512 pour commencer
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
    
    def to_dict(self) -> dict:
        """Convertit la configuration en dictionnaire."""
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "local_models_dir": self.local_models_dir,
            "device": self.device,
            "use_gguf": self.use_gguf,
            "gguf_model_path": self.gguf_model_path,
            "max_length": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "quantize": self.quantize,
            "quantization_bits": self.quantization_bits,
            "max_prompt_length": self.max_prompt_length,
            "enable_auto_calibration": self.enable_auto_calibration,
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


"""Configuration du service de simulation."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


def load_api_conf() -> dict:
    """
    Charge les clés API depuis config/api.conf.
    
    Format attendu : key = value (une ligne par clé)
    
    Returns:
        Dict avec les clés API (gemini_api_key, openai_api_key, etc.)
    """
    # Chemin relatif depuis simulation_service/src/simulation_service/config.py
    # vers config/api.conf à la racine du projet
    project_root = Path(__file__).parent.parent.parent.parent.parent
    api_conf_path = project_root / "config" / "api.conf"
    api_keys = {}
    
    if api_conf_path.exists():
        try:
            # Lire les clés API (format simple key = value)
            with open(api_conf_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Ignorer les lignes vides et les commentaires
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            api_keys[key] = value
        except Exception:
            # En cas d'erreur, ignorer silencieusement
            pass
    
    return api_keys


class Settings(BaseSettings):
    """Paramètres du service de simulation."""

    app_name: str = "simulation-service"
    environment: str = Field("local", description="Tag d'environnement.")
    port: int = Field(4700, description="Port du service.")
    host: str = Field("127.0.0.1", description="Host du service.")
    
    # Intégration memory_service
    memory_service_url: str = Field(
        "http://127.0.0.1:8000",
        description="URL du service mémoire."
    )
    
    # Configuration simulation
    default_max_turns: int = Field(50, description="Nombre maximum de tours par défaut.")
    default_timeout_seconds: int = Field(30, description="Timeout par défaut en secondes.")
    max_concurrent_sessions: int = Field(10, description="Nombre maximum de sessions simultanées.")
    
    # Détection de boucles
    loop_detection_threshold: int = Field(3, description="Nombre de messages identiques pour détecter une boucle.")
    
    # Retry et backoff
    max_retries: int = Field(3, description="Nombre maximum de tentatives.")
    retry_backoff_base: float = Field(1.0, description="Base du backoff exponentiel (secondes).")
    
    # Rate limiting
    max_messages_per_second: int = Field(10, description="Nombre maximum de messages par seconde par agent.")
    
    # API externes (optionnel)
    openai_api_key: Optional[str] = Field(None, description="Clé API OpenAI.")
    anthropic_api_key: Optional[str] = Field(None, description="Clé API Anthropic.")
    gemini_api_key: Optional[str] = Field(None, description="Clé API Gemini.")
    
    # Configuration GPT-2 Local
    local_llm_model: str = Field("gpt2", description="Nom du modèle local (gpt2, distilgpt2).")
    local_llm_max_tokens: int = Field(100, description="Nombre maximum de tokens à générer.")
    local_llm_temperature: float = Field(0.7, description="Température pour la génération (0.0-1.0).")
    local_llm_device: str = Field("auto", description="Device (auto, cpu, cuda).")
    local_llm_quantize: bool = Field(True, description="Activer la quantisation INT4/INT8.")
    local_llm_quantization_bits: int = Field(4, description="Bits de quantisation (4 ou 8).")
    local_llm_max_memory_mb: int = Field(200, description="Mémoire maximale en MB.")
    fallback_to_external_api: bool = Field(True, description="Fallback vers API externe si erreur.")
    
    # Sécurité
    api_token: Optional[str] = Field(None, description="Token d'authentification API.")

    class Config:
        env_prefix = "SIMULATION_SERVICE_"
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialise les settings et charge api.conf."""
        super().__init__(**kwargs)
        
        # Charger les clés API depuis api.conf si non définies dans env
        api_keys = load_api_conf()
        
        # Utiliser les clés de api.conf si non définies ailleurs
        if not self.openai_api_key and 'openai_api_key' in api_keys:
            self.openai_api_key = api_keys['openai_api_key']
        
        if not self.anthropic_api_key and 'anthropic_api_key' in api_keys:
            self.anthropic_api_key = api_keys['anthropic_api_key']
        
        if not self.gemini_api_key and 'gemini_api_key' in api_keys:
            self.gemini_api_key = api_keys['gemini_api_key']


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique de configuration."""
    return Settings()




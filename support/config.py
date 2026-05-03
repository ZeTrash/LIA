"""Configuration du noyau d'appui (Gemini)."""

import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import configparser

logger = logging.getLogger(__name__)


@dataclass
class SupportConfig:
    """Configuration du noyau d'appui."""
    
    # API Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"  # Modèle Gemini par défaut (premier dans la liste de fallback)
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 1024
    
    # API Groq
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"  # Modèle Groq par défaut (mis à jour depuis llama-3.1-70b-versatile décommissionné)
    groq_temperature: float = 0.7
    groq_max_tokens: int = 1024
    
    # Comportement
    enable_learning: bool = True  # Permettre à LIA d'apprendre via Gemini
    auto_save_knowledge: bool = True  # Sauvegarder automatiquement les connaissances apprises
    
    # Limites
    max_queries_per_session: int = 14000  # Limite de requêtes par session
    query_timeout: int = 30  # Timeout en secondes
    
    def load_from_file(self, config_path: str = "config/api.conf") -> None:
        """
        Charge la configuration depuis un fichier.
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Fichier de configuration non trouvé: {config_path}")
            return
        
        try:
            # Essayer d'abord avec ConfigParser (format INI)
            try:
                config = configparser.ConfigParser()
                config.read(config_file)
                
                if "DEFAULT" in config:
                    if "gemini_api_key" in config["DEFAULT"]:
                        self.gemini_api_key = config["DEFAULT"]["gemini_api_key"]
                    if "gemini_model" in config["DEFAULT"]:
                        self.gemini_model = config["DEFAULT"]["gemini_model"]
                    if "groq_api_key" in config["DEFAULT"]:
                        self.groq_api_key = config["DEFAULT"]["groq_api_key"]
                    if "groq_model" in config["DEFAULT"]:
                        self.groq_model = config["DEFAULT"]["groq_model"]
                return
            except (configparser.Error, AttributeError):
                pass
            
            # Sinon, essayer le format simple (ligne par ligne)
            with open(config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "gemini_api_key":
                            self.gemini_api_key = value
                        elif key == "gemini_model":
                            self.gemini_model = value
                        elif key == "groq_api_key":
                            self.groq_api_key = value
                        elif key == "groq_model":
                            self.groq_model = value
        except Exception as e:
            logger.warning(f"Erreur lors du chargement de la configuration: {e}")
    
    def to_dict(self) -> dict:
        """Convertit la configuration en dictionnaire."""
        return {
            "gemini_api_key": self.gemini_api_key,
            "gemini_model": self.gemini_model,
            "gemini_temperature": self.gemini_temperature,
            "gemini_max_tokens": self.gemini_max_tokens,
            "enable_learning": self.enable_learning,
            "auto_save_knowledge": self.auto_save_knowledge,
            "max_queries_per_session": self.max_queries_per_session,
            "query_timeout": self.query_timeout,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SupportConfig":
        """Crée une configuration depuis un dictionnaire."""
        return cls(**data)


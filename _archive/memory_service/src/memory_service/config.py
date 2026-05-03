"""Configuration du service mémoire."""

from functools import lru_cache
from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Paramètres de gouvernance et d'opérations."""

    app_name: str = "memory-service"
    environment: str = Field("local", description="Tag d'environnement.")
    data_dir: str = "data"
    database_url: str = Field(default="sqlite:///./data/memory.db", description="URL de la base SQLite")
    max_memories: int = 12
    context_latency_target_ms: int = 200
    context_payload_soft_limit_bytes: int = 9_000
    context_payload_hard_limit_bytes: int = 10_240
    trait_history_limit: int = 30
    ttl_config: Dict[str, int] = Field(
        default_factory=lambda: {
            "fact": 45,  # jours
            "preference": 180,
            "alert": 15,
        }
    )
    recency_half_life_hours: Dict[str, float] = Field(
        default_factory=lambda: {
            "fact": 24 * 7,  # 1 semaine
            "preference": 24 * 30,
            "alert": 24,  # 1 jour
        }
    )
    governance_threshold_warn: float = 0.35
    governance_threshold_block: float = 0.55
    indicators_window: int = 50

    class Config:
        env_prefix = "MEMORY_SERVICE_"
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique de configuration."""

    return Settings()




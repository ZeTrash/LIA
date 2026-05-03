"""Noyaux d'appui de LIA - Sources de connaissance (Gemini, etc.)."""

__version__ = "0.1.0"

from .knowledge_source import KnowledgeSource
from .config import SupportConfig
from .gemini_adapter import GeminiAdapter
from .learning_service import LearningService
from .support_channel import SupportChannel
from .quality_scorer import QualityScorer, calculate_semantic_distance

__all__ = [
    "KnowledgeSource",
    "SupportConfig",
    "GeminiAdapter",
    "LearningService",
    "SupportChannel",
    "QualityScorer",
    "calculate_semantic_distance",
]


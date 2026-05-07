"""NeuralRouter MVP pour LIA V2.

Rôle:
- classifier l'intention utilisateur vers un ou plusieurs "brains"
- produire un plan de dispatch simple
- agréger les réponses de modules
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List


class BrainType(str, Enum):
    LANG = "lang"
    CODE = "code"
    SELF_IMPROVE = "self_improve"
    VISION = "vision"
    AUDIO = "audio"
    MEMORY = "memory"
    IDENTITY = "identity"
    SYSTEM = "system"


@dataclass(frozen=True)
class IntentClassification:
    brain: BrainType
    sub_tasks: List[str] = field(default_factory=list)
    priority: float = 0.5
    multi_brain: bool = False
    required_brains: List[BrainType] = field(default_factory=list)


@dataclass(frozen=True)
class BrainDispatchPlan:
    primary_brain: BrainType
    parallel_brains: List[BrainType] = field(default_factory=list)
    reason: str = ""


class NeuralRouter:
    """Routeur central V2 (MVP heuristique)."""

    def classify_intent(self, user_input: Any) -> IntentClassification:
        text = str(user_input or "").strip().lower()
        if not text:
            return IntentClassification(
                brain=BrainType.LANG,
                priority=0.2,
                required_brains=[BrainType.LANG],
            )

        code_like = any(k in text for k in ("python", "javascript", "bug", "refactor", "stack trace", "code"))
        self_improve_like = any(
            k in text
            for k in (
                "auto-amélioration",
                "auto amélioration",
                "self improve",
                "self-improve",
                "se recoder",
                "améliore ton code",
                "ameliore ton code",
                "modifie ton code",
            )
        )
        vision_like = any(k in text for k in ("image", "screenshot", "photo", "ocr", "diagramme", "diagram"))
        audio_like = any(k in text for k in ("audio", "voix", "transcrire", "transcription", "tts", "stt"))
        memory_like = any(
            k in text for k in ("souviens", "souvenir", "rappelle", "mémoire", "memoire", "historique")
        )
        identity_like = any(
            k in text
            for k in (
                "qui es-tu",
                "qui es tu",
                "ton identité",
                "ton identite",
                "présente-toi",
                "presente-toi",
                "decris-toi",
                "décris-toi",
                "te décrire",
                "te decrire",
                "parle de toi",
            )
        )
        system_like = any(k in text for k in ("latence", "gpu", "vram", "erreur", "health", "monitoring"))

        required: List[BrainType] = [BrainType.LANG]
        primary = BrainType.LANG
        sub_tasks: List[str] = []

        if self_improve_like:
            primary = BrainType.SELF_IMPROVE
            required.append(BrainType.SELF_IMPROVE)
            sub_tasks.append("self_improvement")
        elif code_like:
            primary = BrainType.CODE
            required.append(BrainType.CODE)
            sub_tasks.append("code_generation_or_debug")
        if vision_like:
            if primary == BrainType.LANG:
                primary = BrainType.VISION
            required.append(BrainType.VISION)
            sub_tasks.append("vision_understanding")
        if audio_like:
            if primary == BrainType.LANG:
                primary = BrainType.AUDIO
            required.append(BrainType.AUDIO)
            sub_tasks.append("audio_processing")
        if memory_like:
            required.append(BrainType.MEMORY)
            sub_tasks.append("memory_retrieval")
        if identity_like:
            if primary == BrainType.LANG:
                primary = BrainType.IDENTITY
            required.append(BrainType.IDENTITY)
            sub_tasks.append("identity_alignment")
        if system_like:
            required.append(BrainType.SYSTEM)
            sub_tasks.append("system_health_check")

        # Dédupliquer en conservant l'ordre
        dedup_required: List[BrainType] = []
        seen = set()
        for b in required:
            if b not in seen:
                dedup_required.append(b)
                seen.add(b)

        urgency = 0.5
        if re.search(r"\b(urgent|critique|immédiat|immediat|now)\b", text):
            urgency = 0.9
        elif system_like:
            urgency = 0.75

        return IntentClassification(
            brain=primary,
            sub_tasks=sub_tasks,
            priority=urgency,
            multi_brain=len(dedup_required) > 1,
            required_brains=dedup_required,
        )

    def dispatch(self, intent: IntentClassification) -> BrainDispatchPlan:
        parallel = [b for b in intent.required_brains if b != intent.brain]
        reason = f"primary={intent.brain.value}, parallel={[b.value for b in parallel]}"
        return BrainDispatchPlan(
            primary_brain=intent.brain,
            parallel_brains=parallel,
            reason=reason,
        )

    def aggregate(self, responses: Dict[BrainType, str]) -> str:
        """Agrégation minimale: LANG en priorité, sinon concaténation stable."""
        if BrainType.LANG in responses and responses[BrainType.LANG]:
            return responses[BrainType.LANG]
        ordered = [responses[b] for b in BrainType if b in responses and responses[b]]
        return "\n".join(ordered).strip()


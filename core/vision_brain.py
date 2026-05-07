"""VisionBrain MVP stub."""

from __future__ import annotations

from typing import Optional


class VisionBrain:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def analyze(self, message: str, context: Optional[str] = None) -> str:
        _ = context
        return (
            "VisionBrain est activé (MVP). "
            f"Modèle configuré: {self.model_name}. "
            "Aucun pipeline image/OCR branché dans cette étape; "
            "j'ai routé la demande vers le canal vision."
        )


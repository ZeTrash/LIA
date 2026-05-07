"""AudioBrain MVP stub."""

from __future__ import annotations


class AudioBrain:
    def __init__(self, stt_model: str, tts_model: str) -> None:
        self.stt_model = stt_model
        self.tts_model = tts_model

    def process(self, message: str) -> str:
        _ = message
        return (
            "AudioBrain est activé (MVP). "
            f"STT={self.stt_model}, TTS={self.tts_model}. "
            "Le pipeline voix complet (transcription/synthèse) sera branché dans l'étape suivante."
        )


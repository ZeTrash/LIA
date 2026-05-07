"""CodeBrain MVP: génération de code dédiée via vLLM."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class CodeBrain:
    """Brain spécialisé code (chargement lazy)."""

    def __init__(
        self,
        model_name: str,
        dtype: str = "float16",
        max_model_len: int = 8192,
        gpu_memory_utilization: float = 0.2,
        cache_dir: str = "models/hf_cache",
    ) -> None:
        self.model_name = model_name
        self.dtype = dtype
        self.max_model_len = max_model_len
        self.gpu_memory_utilization = gpu_memory_utilization
        self.cache_dir = str(Path(cache_dir).resolve())
        self._model = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        from vllm import LLM

        self._model = LLM(
            model=self.model_name,
            dtype=self.dtype,
            max_model_len=self.max_model_len,
            gpu_memory_utilization=self.gpu_memory_utilization,
            download_dir=self.cache_dir,
            hf_overrides={"cache_dir": self.cache_dir},
        )

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.95,
        top_k: int = 40,
        repetition_penalty: float = 1.05,
    ) -> str:
        self._ensure_model()
        from vllm import SamplingParams

        sampling = SamplingParams(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
        )
        outputs = self._model.generate([prompt], sampling_params=sampling)
        if not outputs or not outputs[0].outputs:
            return ""
        return outputs[0].outputs[0].text

    def close(self) -> None:
        if self._model is None:
            return
        try:
            if hasattr(self._model, "llm_engine") and hasattr(self._model.llm_engine, "shutdown"):
                self._model.llm_engine.shutdown()
        except Exception:
            pass
        self._model = None


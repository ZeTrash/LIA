"""InteroceptionBrain MVP: monitoring interne runtime."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import os
import subprocess
from typing import Any, Deque, Dict, Optional


@dataclass
class RequestMetric:
    latency_ms: float
    success: bool
    timestamp_iso: str


class InteroceptionBrain:
    """Collecte des signaux opérationnels simples pour health/reporting."""

    def __init__(self, max_history: int = 200) -> None:
        self.max_history = max_history
        self._history: Deque[RequestMetric] = deque(maxlen=max_history)
        self._module_health: Dict[str, str] = {}
        self._last_error_by_module: Dict[str, Optional[str]] = {}
        self._queue_depth: int = 0
        self._last_system_sample: Dict[str, Any] = {}
        # Throttle policy (MVP)
        self.max_queue_depth_before_throttle = int(os.getenv("LIA_MAX_QUEUE_DEPTH_BEFORE_THROTTLE", "4"))
        self.max_gpu_mem_util_before_throttle = float(os.getenv("LIA_MAX_GPU_MEM_UTIL_BEFORE_THROTTLE", "0.90"))

    def record_request(self, latency_ms: float, success: bool) -> None:
        self._history.append(
            RequestMetric(
                latency_ms=float(latency_ms),
                success=bool(success),
                timestamp_iso=datetime.now().isoformat(),
            )
        )

    def set_module_health(self, module: str, status: str, last_error: Optional[str] = None) -> None:
        self._module_health[module] = status
        self._last_error_by_module[module] = last_error

    def inc_queue_depth(self) -> None:
        self._queue_depth += 1

    def dec_queue_depth(self) -> None:
        self._queue_depth = max(0, self._queue_depth - 1)

    def sample_system_stats(self) -> Dict[str, Any]:
        """Best-effort GPU/VRAM/temp sampling.

        - torch.cuda: mémoire allouée/réservée/total si dispo
        - rocm-smi/nvidia-smi: température/usage si disponible
        """
        stats: Dict[str, Any] = {"timestamp": datetime.now().isoformat()}

        # torch cuda memory
        try:
            import torch

            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                props = torch.cuda.get_device_properties(device)
                total = float(getattr(props, "total_memory", 0.0) or 0.0)
                alloc = float(torch.cuda.memory_allocated(device))
                reserved = float(torch.cuda.memory_reserved(device))
                util = (reserved / total) if total else 0.0
                stats.update(
                    {
                        "cuda_device": int(device),
                        "gpu_name": getattr(props, "name", None),
                        "gpu_mem_total_bytes": int(total),
                        "gpu_mem_allocated_bytes": int(alloc),
                        "gpu_mem_reserved_bytes": int(reserved),
                        "gpu_mem_util": round(util, 4),
                    }
                )
        except Exception:
            pass

        # rocm-smi (AMD) or nvidia-smi (NVIDIA) temperatures
        for cmd in (["rocm-smi", "--showtemp", "--showuse", "--json"], ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"]):
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=2, check=False)
                if out.returncode != 0:
                    continue
                txt = (out.stdout or "").strip()
                if not txt:
                    continue
                stats["gpu_raw"] = txt[:2000]
                stats["gpu_tool"] = cmd[0]
                break
            except Exception:
                continue

        self._last_system_sample = stats
        return stats

    def should_throttle(self) -> Dict[str, Any]:
        """Décide un throttling simple et propose un facteur sur max_tokens."""
        sample = self._last_system_sample or self.sample_system_stats()
        gpu_util = float(sample.get("gpu_mem_util") or 0.0)
        throttled = False
        factor = 1.0
        reasons = []
        if self._queue_depth >= self.max_queue_depth_before_throttle:
            throttled = True
            factor = min(factor, 0.5)
            reasons.append("queue_depth")
        if gpu_util and gpu_util >= self.max_gpu_mem_util_before_throttle:
            throttled = True
            factor = min(factor, 0.6)
            reasons.append("gpu_mem_util")
        return {
            "throttled": throttled,
            "max_tokens_factor": round(factor, 3),
            "queue_depth": self._queue_depth,
            "reasons": reasons,
        }

    def get_health_report(self) -> Dict[str, Any]:
        n = len(self._history)
        ok = sum(1 for h in self._history if h.success)
        avg_latency = (sum(h.latency_ms for h in self._history) / n) if n else 0.0
        success_rate = (ok / n) if n else 1.0
        system = self._last_system_sample or self.sample_system_stats()
        throttle = self.should_throttle()
        return {
            "timestamp": datetime.now().isoformat(),
            "request_count_window": n,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(success_rate, 4),
            "queue_depth": self._queue_depth,
            "system": system,
            "throttle": throttle,
            "module_health": dict(self._module_health),
            "last_error_by_module": dict(self._last_error_by_module),
        }


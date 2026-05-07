"""Smoke test vLLM local sur GPU (ROCm/CUDA)."""

import argparse
import gc
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import CoreConfig, LLMAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test vLLM backend pour LIA")
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Nom HuggingFace du modèle à charger",
    )
    parser.add_argument(
        "--prompt",
        default="Présente-toi en une phrase concise.",
        help="Prompt de test",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=96,
        help="Nombre max de tokens générés",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=8192,
        help="Longueur de contexte max pour vLLM",
    )
    args = parser.parse_args()

    config = CoreConfig(
        model_name=args.model,
        backend="vllm",
        use_gguf=False,
        max_length=args.max_new_tokens,
        max_prompt_length=args.max_model_len,
        vllm_max_model_len=args.max_model_len,
        vllm_dtype="float16",
        vllm_gpu_memory_utilization=0.8,
        enable_auto_calibration=False,
    )

    adapter = None
    backend_name = "unknown"
    response = ""
    try:
        adapter = LLMAdapter(
            config=config,
            use_memory=False,
            use_cognitive_planner=False,
            use_phrase_memory=False,
        )
        backend_name = adapter.backend_type
        response = adapter._generate_vllm(args.prompt).strip()
    finally:
        if adapter is not None:
            adapter.close()
        try:
            import torch.distributed as dist

            if dist.is_available() and dist.is_initialized():
                dist.destroy_process_group()
        except Exception:
            pass
        gc.collect()

    print("=" * 70)
    print("vLLM Smoke Test")
    print("=" * 70)
    print(f"Backend: {backend_name}")
    print(f"Model:   {args.model}")
    print(f"Prompt:  {args.prompt}")
    print("-" * 70)
    print(response or "<empty response>")
    print("=" * 70)

    return 0 if response else 1


if __name__ == "__main__":
    raise SystemExit(main())

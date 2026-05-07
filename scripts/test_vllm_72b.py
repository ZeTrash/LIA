"""Validation ciblée Qwen2.5-72B sur vLLM avec budget VRAM."""

import argparse
import gc
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import CoreConfig, LLMAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Test vLLM Qwen2.5-72B (MI300X)")
    parser.add_argument("--model", default="Qwen/Qwen2.5-72B-Instruct")
    parser.add_argument("--prompt", default="Explique en 5 points comment planifier une migration LLM en production.")
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--gpu-mem", type=float, default=0.92, help="vllm gpu_memory_utilization")
    parser.add_argument("--dtype", default="float16", help="float16|bfloat16|auto")
    args = parser.parse_args()

    cfg = CoreConfig(
        model_name=args.model,
        backend="vllm",
        use_gguf=False,
        max_length=args.max_new_tokens,
        max_prompt_length=args.max_model_len,
        vllm_max_model_len=args.max_model_len,
        vllm_dtype=args.dtype,
        vllm_gpu_memory_utilization=args.gpu_mem,
        enable_auto_calibration=False,
    )

    adapter = None
    backend_name = "unknown"
    response = ""
    t0 = time.perf_counter()
    try:
        adapter = LLMAdapter(
            config=cfg,
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

    elapsed = time.perf_counter() - t0
    print("=" * 70)
    print("vLLM 72B Validation")
    print("=" * 70)
    print(f"Backend: {backend_name}")
    print(f"Model:   {args.model}")
    print(f"DType:   {args.dtype}")
    print(f"GPU mem: {args.gpu_mem}")
    print(f"Latency: {elapsed:.2f}s")
    print("-" * 70)
    print(response or "<empty response>")
    print("=" * 70)
    return 0 if response else 1


if __name__ == "__main__":
    raise SystemExit(main())

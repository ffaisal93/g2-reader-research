#!/usr/bin/env python3
"""Run only the frozen official G2 Content Graph construction stage."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    lab_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-id", default="spiqa_58")
    parser.add_argument(
        "--official-root",
        type=Path,
        default=lab_root / "baseline_original" / "G2_Reader_official_trace",
    )
    parser.add_argument("--memory-dir", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--llm-base-url", default="http://127.0.0.1:18000/v1")
    parser.add_argument("--embedding-base-url", default="http://127.0.0.1:18001/v1")
    parser.add_argument("--chat-model", default="local-qwen-vl")
    parser.add_argument("--embedding-model", default="local-bge-m3")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--embedding-batch-size", type=int, default=64)
    parser.add_argument("--analysis-max-tokens", type=int, default=1536)
    parser.add_argument("--text-analysis-max-tokens", type=int, default=768)
    parser.add_argument("--image-analysis-max-tokens", type=int, default=1536)
    parser.add_argument("--evolution-max-tokens", type=int, default=1024)
    parser.add_argument(
        "--evolution-summary-text-neighbors",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--parallel-analysis",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--evolution-rounds", type=int, default=1)
    parser.add_argument("--window-size", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--request-timeout-seconds", type=int, default=3600)
    return parser.parse_args()


def endpoint_is_ready(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/models", timeout=10) as response:
            return response.status == 200
    except Exception:
        return False


def main() -> int:
    args = parse_args()
    args.official_root = args.official_root.resolve()
    args.memory_dir = args.memory_dir.resolve()
    args.result_json = args.result_json.resolve()

    if not endpoint_is_ready(args.llm_base_url):
        raise RuntimeError(f"VLM endpoint is not ready: {args.llm_base_url}")
    if not endpoint_is_ready(args.embedding_base_url):
        raise RuntimeError(f"Embedding endpoint is not ready: {args.embedding_base_url}")

    final_graph_dir = args.memory_dir / f"{args.question_id}_iter_{args.evolution_rounds}"
    if final_graph_dir.exists():
        raise FileExistsError(
            f"Cold-build output already exists: {final_graph_dir}. "
            "Select a new memory directory."
        )

    args.memory_dir.mkdir(parents=True, exist_ok=True)
    args.result_json.parent.mkdir(parents=True, exist_ok=True)

    os.environ.update(
        {
            "G2_USE_LOCAL_RUNTIME": "1",
            "G2_LAB_ROOT": str(Path(__file__).resolve().parents[2]),
            "G2_LLM_BASE_URL": args.llm_base_url,
            "G2_EMBED_BASE_URL": args.embedding_base_url,
            "G2_API_KEY": "local",
            "G2_EMBED_API_KEY": "local",
            "G2_CHAT_MODEL": args.chat_model,
            "G2_EMBED_MODEL": args.embedding_model,
            "G2_MEMORY_DIR": str(args.memory_dir),
            "G2_MAX_CONCURRENCY": str(args.concurrency),
            "G2_EMBED_BATCH_SIZE": str(args.embedding_batch_size),
            "G2_ANALYSIS_MAX_TOKENS": str(args.analysis_max_tokens),
            "G2_TEXT_ANALYSIS_MAX_TOKENS": str(args.text_analysis_max_tokens),
            "G2_IMAGE_ANALYSIS_MAX_TOKENS": str(args.image_analysis_max_tokens),
            "G2_EVOLUTION_MAX_TOKENS": str(args.evolution_max_tokens),
            "G2_EVOLUTION_SUMMARY_TEXT_NEIGHBORS": (
                "1" if args.evolution_summary_text_neighbors else "0"
            ),
            "G2_PARALLEL_ANALYSIS": "1" if args.parallel_analysis else "0",
            "G2_REQUEST_TIMEOUT_SECONDS": str(args.request_timeout_seconds),
            "G2_RANDOM_SEED": str(args.seed),
            "PYTHONHASHSEED": str(args.seed),
        }
    )
    sys.path.insert(0, str(args.official_root))

    from prebuild.amem_new import construct_memory
    from prebuild.usage_tracker import get_and_reset, reset_usage

    reset_usage()
    started = time.time()
    status = "failed"
    error = None
    memory_system = None
    try:
        memory_system = asyncio.run(
            construct_memory(
                args.question_id,
                evolve_iters=args.evolution_rounds,
                window_size=args.window_size,
            )
        )
        status = "complete"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        duration = time.time() - started
        usage = get_and_reset()
        result = {
            "status": status,
            "error": error,
            "question_id": args.question_id,
            "duration_total_sec": duration,
            "node_count": len(memory_system.memories) if memory_system is not None else None,
            "configuration": {
                "official_root": str(args.official_root),
                "memory_dir": str(args.memory_dir),
                "llm_base_url": args.llm_base_url,
                "embedding_base_url": args.embedding_base_url,
                "chat_model": args.chat_model,
                "embedding_model": args.embedding_model,
                "concurrency": args.concurrency,
                "embedding_batch_size": args.embedding_batch_size,
                "analysis_max_tokens": args.analysis_max_tokens,
                "text_analysis_max_tokens": args.text_analysis_max_tokens,
                "image_analysis_max_tokens": args.image_analysis_max_tokens,
                "evolution_max_tokens": args.evolution_max_tokens,
                "evolution_summary_text_neighbors": args.evolution_summary_text_neighbors,
                "parallel_analysis": args.parallel_analysis,
                "evolution_rounds": args.evolution_rounds,
                "window_size": args.window_size,
                "seed": args.seed,
            },
            "usage": usage,
        }
        args.result_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

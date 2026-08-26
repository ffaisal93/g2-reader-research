"""Run the corrected upstream entry point from a versioned non-secret profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


LAB = Path(__file__).resolve().parents[2]
PATCHED = LAB / "baseline_original" / "G2_Reader_patched"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--debug", action="store_true", help="run only the first row through released debug mode")
    parser.add_argument("--document-limit", type=int, help="override profile; zero means all")
    parser.add_argument("--evolution-rounds", type=int, help="override profile")
    args = parser.parse_args()
    profile = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    runtime = dict(profile["runtime"])
    if args.document_limit is not None:
        runtime["document_limit"] = args.document_limit
    if args.evolution_rounds is not None:
        runtime["evolution_rounds"] = args.evolution_rounds
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty result directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    effective_data_path = args.data_path.resolve()
    if args.debug:
        debug_path = args.output_dir / "debug_input.jsonl"
        first_row = next(line for line in args.data_path.read_text(encoding="utf-8").splitlines() if line.strip())
        debug_path.write_text(first_row + "\n", encoding="utf-8")
        effective_data_path = debug_path.resolve()
    resolved = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile | {"runtime": runtime},
        "data_path": str(args.data_path.resolve()),
        "effective_data_path": str(effective_data_path),
        "debug": args.debug,
    }
    resolved["configuration_hash"] = hashlib.sha256(
        json.dumps(resolved["profile"] | {"data_path": resolved["data_path"], "debug": args.debug}, sort_keys=True).encode()
    ).hexdigest()[:16]
    (args.output_dir / "run_manifest.json").write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")

    key_name = profile["models"]["api_key_env"]
    if not os.environ.get(key_name):
        raise RuntimeError(f"required environment variable is unset: {key_name}")
    env = os.environ.copy()
    env.update(
        {
            "G2_LLM_BASE_URL": profile["models"]["api_base"],
            "G2_CHAT_MODEL": profile["models"]["chat_model"],
            "G2_EMBED_MODEL": profile["models"]["embedding_model"],
            "G2_MAX_CONCURRENCY": str(runtime["concurrency"]),
        }
    )
    command = [
        sys.executable,
        "-m",
        "scripts.test_rag",
        "--data_path",
        str(effective_data_path),
        "--save_dir",
        str(args.output_dir.resolve()),
        "--model",
        profile["models"]["chat_model"],
        "--n_proc",
        str(runtime["n_proc"]),
        "--use_dag",
        "--max_context_tokens",
        str(runtime["max_context_tokens"]),
        "--evolution_rounds",
        str(runtime["evolution_rounds"]),
        "--document_limit",
        str(runtime["document_limit"]),
        "--top_k",
        str(runtime["top_k"]),
        "--top_k_text_kw",
        str(runtime["top_k_text_kw"]),
        "--top_k_image_kw",
        str(runtime["top_k_image_kw"]),
    ]
    if args.debug:
        command.append("--debug")
    subprocess.run(command, cwd=PATCHED, env=env, check=True)
    predictions = args.output_dir / f"{profile['models']['chat_model']}_dag_rag_1.jsonl"
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("render_traces.py")), "--input", str(predictions), "--output-dir", str(args.output_dir / "traces")],
        cwd=LAB,
        check=True,
    )


if __name__ == "__main__":
    main()

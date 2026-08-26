"""Gate and launch the official G² SPIQA audit without changing model behavior."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
PYTHON = LAB / ".venv" / "bin" / "python"
RUNNER = LAB / "scripts" / "run_official_audit.py"
OFFICIAL = LAB / "baseline_original" / "G2_Reader_official_trace"
QUESTIONS = LAB / "data" / "slices" / "official_trace" / "spiqa_100_v1.jsonl"
AUDITS = LAB / "results" / "official_trace" / "audits"
MEMORY = LAB / "results" / "official_trace" / "memory_systems_qwen3_official_fixedseed_v5"
GATE = AUDITS / "qwen3_official_fixedseed_gate_v5"
PILOT = AUDITS / "qwen3_official_fixedseed_pilot5_v8"
FULL = AUDITS / "qwen3_official_fixedseed_spiqa100_v8"
STATUS = AUDITS / "qwen3_official_audit_sequence_status.json"


def save_status(stage: str, state: str, **details) -> None:
    payload = {"stage": stage, "state": state, "updated_at_unix": time.time(), **details}
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATUS)


def endpoint_healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status == 200
    except Exception:
        return False


def validate_run(run_dir: Path, expected: int) -> None:
    statuses = sorted(run_dir.glob("questions/*/status.json"))
    if len(statuses) != expected:
        raise RuntimeError(f"{run_dir.name}: expected {expected} statuses, found {len(statuses)}")
    for status_path in statuses:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") != "complete":
            raise RuntimeError(f"{run_dir.name}: non-complete question: {status}")
        question_dir = status_path.parent
        predictions = list((question_dir / "official_output").glob("*_dag_rag_1.jsonl"))
        retrieval = question_dir / "official_output" / "logs" / f"data_{status['question_id']}" / "retrieval_results.jsonl"
        trace = question_dir / "official_output" / "logs" / f"data_{status['question_id']}" / "official_trace.jsonl"
        console = question_dir / "console.log"
        if not predictions or not any(path.stat().st_size for path in predictions):
            raise RuntimeError(f"{status['question_id']}: missing prediction")
        prediction_rows = [
            json.loads(line)
            for path in predictions
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not prediction_rows or not str(prediction_rows[-1].get("pred", "")).strip():
            raise RuntimeError(f"{status['question_id']}: empty parsed prediction")
        if not retrieval.exists() or retrieval.stat().st_size == 0:
            raise RuntimeError(f"{status['question_id']}: missing retrieval trace")
        if not trace.exists() or trace.stat().st_size == 0:
            raise RuntimeError(f"{status['question_id']}: missing passive execution trace")
        if not console.exists():
            raise RuntimeError(f"{status['question_id']}: missing console log")
        console_text = console.read_text(encoding="utf-8", errors="replace")
        fatal_markers = (
            "Traceback (most recent call last)",
            "Error when evolving memory note",
            "[evolve] API error",
            "[ERROR] Embedding request failed",
            "Retriever error:",
            "Retriever (split sem+BM25) error:",
        )
        found = [marker for marker in fatal_markers if marker in console_text]
        if found:
            raise RuntimeError(f"{status['question_id']}: infrastructure failure markers: {found}")
        # A malformed/truncated structured response is allowed only when the
        # bounded retry recovers it.  The released preprocessing code otherwise
        # substitutes a default note and silently builds an incomplete graph.
        incomplete_analysis_patterns = (
            r"warning:\s*[1-9]\d*/\d+\s+(?:text chunks|image) analysis failed",
            r"text notes added successfully:.*?\b[1-9]\d* failed",
            r"image notes added successfully:.*?\b[1-9]\d* failed",
        )
        incomplete = [
            pattern for pattern in incomplete_analysis_patterns
            if re.search(pattern, console_text, flags=re.IGNORECASE)
        ]
        if incomplete:
            raise RuntimeError(
                f"{status['question_id']}: incomplete Content Graph preprocessing: {incomplete}"
            )
        if "Initial retrieval complete: Number of text blocks 0, Image count 0" in console_text:
            raise RuntimeError(f"{status['question_id']}: initial retrieval returned no evidence")
        memory_dir = MEMORY / f"{status['question_id']}_iter_1"
        required_memory = (memory_dir / "memories.pkl", memory_dir / "retriever_embeddings.npy")
        if not all(path.exists() and path.stat().st_size > 10 for path in required_memory):
            raise RuntimeError(f"{status['question_id']}: missing evolved Content Graph artifacts")


def run_audit(output: Path, limit: int | None) -> None:
    if output.exists() and any(output.glob("questions/*/status.json")):
        completed = len(list(output.glob("questions/*/status.json")))
        save_status(output.name, "resuming", completed_questions=completed)
    command = [
        str(PYTHON), "-u", str(RUNNER),
        "--official-root", str(OFFICIAL),
        "--questions", str(QUESTIONS),
        "--output-dir", str(output),
        "--memory-dir", str(MEMORY),
        "--python", str(PYTHON),
        "--model", "local-qwen-vl",
        "--embedding-model", "local-bge-m3",
        "--base-url", "http://127.0.0.1:18000/v1",
        "--embedding-base-url", "http://127.0.0.1:18001/v1",
        "--max-concurrency", "8",
        "--request-timeout-seconds", "3600",
        "--seed", "42",
        "--timeout-seconds", "21600",
        "--max-question-attempts", "2",
    ]
    if limit is not None:
        command.extend(["--limit", str(limit)])
    output.mkdir(parents=True, exist_ok=True)
    with (output / "sequence_launcher.log").open("a", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=LAB, stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"runner exited {result.returncode} for {output.name}")


def main() -> None:
    try:
        if not endpoint_healthy("http://127.0.0.1:18000/v1/models"):
            raise RuntimeError("Qwen3 vLLM endpoint is unavailable")
        if not endpoint_healthy("http://127.0.0.1:18001/v1/models"):
            raise RuntimeError("BGE-M3 embedding endpoint is unavailable")

        save_status("one_question_gate", "running")
        run_audit(GATE, limit=1)
        validate_run(GATE, expected=1)

        save_status("pilot_5", "running")
        run_audit(PILOT, limit=5)
        validate_run(PILOT, expected=5)

        free_gib = shutil.disk_usage(LAB).free / (1024 ** 3)
        if free_gib < 5:
            raise RuntimeError(f"only {free_gib:.2f} GiB free after pilot; refusing full audit")

        save_status("audit_100", "running", free_gib=round(free_gib, 2))
        run_audit(FULL, limit=None)
        validate_run(FULL, expected=100)
        save_status("complete", "complete", question_count=100)
    except Exception as exc:
        save_status("blocked", "failed", error=str(exc))
        raise


if __name__ == "__main__":
    main()

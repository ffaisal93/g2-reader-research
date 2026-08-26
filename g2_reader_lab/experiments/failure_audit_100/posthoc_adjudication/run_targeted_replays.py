#!/usr/bin/env python3
"""Resume a targeted 32B-reader replay set on the same optimized-8B graphs."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


LAB = Path("/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab")
ROOT = LAB / "experiments/failure_audit_100/posthoc_adjudication"
AUDIT = ROOT.parent
GRAPH_ROOT = AUDIT / "graphs"
OUTPUT = ROOT / "teacher_replays"
RUNNER = LAB / "experiments/low_resource_content_graph/loss_evaluation/run_matched_qa.sh"
PROGRESS = ROOT / "REPLAY_PROGRESS.json"

# Covers the dominant Worker class, retrieval (visual and text), every observed
# decomposition/composition case, and one raw-correct parser case.
TARGETS = [
    "spiqa_39",
    "spiqa_4", "spiqa_110", "spiqa_116", "spiqa_522",
    "spiqa_163", "spiqa_195", "spiqa_396",
    "spiqa_44", "spiqa_571", "spiqa_47",
]


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def prediction_file(question_id: str) -> Path:
    return OUTPUT / question_id / "local-qwen-vl_dag_rag_1.jsonl"


def load_progress() -> dict[str, Any]:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"targets": TARGETS, "states": {question_id: {"status": "pending", "attempts": 0} for question_id in TARGETS}}


def prediction_summary(question_id: str) -> dict[str, Any]:
    row = json.loads(prediction_file(question_id).read_text(encoding="utf-8").splitlines()[0])
    return {
        "prediction": row.get("pred"), "reference": row.get("answer"),
        "raw_response_present": bool(str(row.get("response") or "").strip()),
        "process_time": row.get("process_time"), "usage": {
            key: value for key, value in (row.get("usage") or {}).items() if key != "calls"
        },
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    progress = load_progress()
    for question_id in TARGETS:
        state = progress["states"].setdefault(question_id, {"status": "pending", "attempts": 0})
        if prediction_file(question_id).exists() and prediction_file(question_id).stat().st_size > 0:
            state.update({"status": "complete", **prediction_summary(question_id)})
            atomic_json(PROGRESS, progress)
            continue
        # A partial directory is evidence from an interrupted/failed attempt.
        # Preserve it and avoid destructive overwrite; use a fresh attempt path.
        attempt = int(state.get("attempts", 0)) + 1
        output_dir = OUTPUT / question_id
        if output_dir.exists():
            output_dir = OUTPUT / f"{question_id}_attempt_{attempt}"
        state.update({"status": "running", "attempts": attempt, "started_at": time.time(), "output_dir": str(output_dir)})
        atomic_json(PROGRESS, progress)
        input_path = AUDIT / "questions" / question_id / "input.jsonl"
        log_path = OUTPUT / f"{question_id}_console.log"
        started = time.time()
        try:
            with log_path.open("w", encoding="utf-8") as log:
                completed = subprocess.run(
                    ["bash", str(RUNNER), question_id, str(GRAPH_ROOT), str(output_dir), str(input_path)],
                    cwd=LAB, stdout=log, stderr=subprocess.STDOUT, timeout=900, check=False,
                )
            state.update({
                "status": "complete" if completed.returncode == 0 else "failed",
                "return_code": completed.returncode, "duration_seconds": time.time() - started,
                "finished_at": time.time(),
            })
            candidate = output_dir / "local-qwen-vl_dag_rag_1.jsonl"
            if completed.returncode == 0 and candidate.exists():
                # Normal first-attempt path is what prediction_summary expects.
                if output_dir == OUTPUT / question_id:
                    state.update(prediction_summary(question_id))
                else:
                    row = json.loads(candidate.read_text(encoding="utf-8").splitlines()[0])
                    state.update({"prediction": row.get("pred"), "reference": row.get("answer"), "process_time": row.get("process_time")})
        except subprocess.TimeoutExpired:
            state.update({"status": "failed", "return_code": None, "duration_seconds": time.time() - started, "error": "timeout"})
        atomic_json(PROGRESS, progress)
    progress["finished_at"] = time.time()
    atomic_json(PROGRESS, progress)


if __name__ == "__main__":
    main()

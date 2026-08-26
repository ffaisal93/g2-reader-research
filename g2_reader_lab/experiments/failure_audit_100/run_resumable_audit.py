#!/usr/bin/env python3
"""Run the 100-question low-resource G2 audit with durable checkpoints.

The frozen official source remains untouched.  Every question has independent
build and query states.  Re-running this program skips validated work, archives
failed partial attempts, restarts unhealthy local services, and resumes at the
first incomplete stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any


LAB = Path("/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab")
ROOT = LAB / "experiments/failure_audit_100"
SOURCE = LAB / "experiments/low_resource_content_graph/implementations/student_8b_behavior_preserving"
QUESTIONS = LAB / "data/slices/official_trace/spiqa_100_v1.jsonl"
PYTHON = LAB / ".venv/bin/python"
VLLM = LAB / ".venv-vllm/bin/vllm"
BUILD_RUNNER = LAB / "experiments/low_resource_content_graph/run_content_graph.py"
QA_RUNNER = LAB / "experiments/low_resource_content_graph/loss_evaluation/run_matched_qa.sh"
VLM_MODEL = Path("/mnt/maxtox-nfs-student/zff/models/qwen3-vl-8b-instruct-fp8")
EMBED_MODEL = Path("/mnt/maxtox-nfs-student/zff/models/bge-m3")
GRAPH_ROOT = ROOT / "graphs"
QUESTION_ROOT = ROOT / "questions"
FAILED_ROOT = ROOT / "failed_attempts"
SERVICE_LOG = ROOT / "service_logs"
JOURNAL = ROOT / "journal.jsonl"
PROGRESS = ROOT / "PROGRESS.json"
REPORT = ROOT / "REPORT.md"
FINDINGS = ROOT / "FINDINGS.md"

VLM_URL = "http://127.0.0.1:18000/v1"
EMBED_URL = "http://127.0.0.1:18001/v1"
VLM_SESSION = "g2_audit100_vlm"
EMBED_SESSION = "g2_audit100_embed"

REUSABLE_GRAPHS = {
    "spiqa_58": LAB / "experiments/low_resource_content_graph/results/final_v1/spiqa_58/memory_systems",
    "spiqa_108": LAB / "experiments/low_resource_content_graph/results/final_v1/spiqa_108/memory_systems",
    "spiqa_378": LAB / "experiments/low_resource_content_graph/results/expansion_v3/spiqa_378/memory_systems",
    "spiqa_540": LAB / "experiments/low_resource_content_graph/loss_evaluation/candidate_builds/spiqa_540/memory_systems",
    "spiqa_542": LAB / "experiments/low_resource_content_graph/loss_evaluation/candidate_builds/spiqa_542/memory_systems",
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def append_event(event: str, **details: Any) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": time.time(), "event": event, **details}
    with JOURNAL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def endpoint_ready(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/models", timeout=10) as response:
            return response.status == 200
    except Exception:
        return False


def wait_endpoint(base_url: str, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if endpoint_ready(base_url):
            return True
        time.sleep(2)
    return False


def tmux_has(session: str) -> bool:
    return subprocess.run(
        ["tmux", "has-session", "-t", session],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def stop_tmux(session: str) -> None:
    if tmux_has(session):
        subprocess.run(["tmux", "kill-session", "-t", session], check=False)


def start_tmux(session: str, command: str) -> None:
    stop_tmux(session)
    subprocess.run(["tmux", "new-session", "-d", "-s", session, command], check=True)


def ensure_embedding_service() -> None:
    if endpoint_ready(EMBED_URL):
        return
    SERVICE_LOG.mkdir(parents=True, exist_ok=True)
    log = SERVICE_LOG / "embedding.log"
    command = (
        f"cd {shlex.quote(str(LAB))} && exec {shlex.quote(str(PYTHON))} -u "
        f"environment/local_embedding_server.py --model {shlex.quote(str(EMBED_MODEL))} "
        f"--device cuda --host 127.0.0.1 --port 18001 >> {shlex.quote(str(log))} 2>&1"
    )
    append_event("service_start", service="embedding")
    start_tmux(EMBED_SESSION, command)
    if not wait_endpoint(EMBED_URL, 240):
        raise RuntimeError("embedding service did not become ready")


def ensure_vlm_service() -> None:
    if endpoint_ready(VLM_URL):
        return
    SERVICE_LOG.mkdir(parents=True, exist_ok=True)
    log = SERVICE_LOG / "vllm.log"
    command = (
        f"cd {shlex.quote(str(LAB))} && export VLLM_USE_FLASHINFER_SAMPLER=0 && "
        f"exec {shlex.quote(str(VLLM))} serve {shlex.quote(str(VLM_MODEL))} "
        "--host 127.0.0.1 --port 18000 --served-model-name local-qwen-vl "
        "--max-model-len 24000 --gpu-memory-utilization 0.88 --max-num-seqs 24 "
        "--limit-mm-per-prompt '{\"image\":8}' --generation-config vllm "
        "--structured-outputs-config '{\"backend\":\"xgrammar\",\"disable_any_whitespace\":true}' "
        f">> {shlex.quote(str(log))} 2>&1"
    )
    append_event("service_start", service="vlm")
    start_tmux(VLM_SESSION, command)
    if not wait_endpoint(VLM_URL, 600):
        raise RuntimeError("VLM service did not become ready")


def ensure_services() -> None:
    # BGE-M3 occupies little memory. Start it first so vLLM profiles the actual
    # remaining device memory, matching the validated five-question setup.
    ensure_embedding_service()
    ensure_vlm_service()


def valid_graph(question_id: str) -> bool:
    graph = GRAPH_ROOT / f"{question_id}_iter_1"
    return all(
        path.exists() and path.stat().st_size > 10
        for path in (graph / "memories.pkl", graph / "retriever_embeddings.npy")
    )


def install_reusable_graphs() -> None:
    GRAPH_ROOT.mkdir(parents=True, exist_ok=True)
    for question_id, source_root in REUSABLE_GRAPHS.items():
        for iteration in (0, 1):
            source = source_root / f"{question_id}_iter_{iteration}"
            target = GRAPH_ROOT / f"{question_id}_iter_{iteration}"
            if source.exists() and not target.exists():
                target.symlink_to(source, target_is_directory=True)
                append_event(
                    "graph_reused",
                    question_id=question_id,
                    iteration=iteration,
                    source=str(source),
                )


def archive_path(path: Path, question_id: str, stage: str, attempt: int) -> None:
    if not path.exists() and not path.is_symlink():
        return
    destination = FAILED_ROOT / question_id / f"{stage}_attempt_{attempt}_{time.time_ns()}" / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(destination))


def load_state(question_id: str) -> dict[str, Any]:
    path = QUESTION_ROOT / question_id / "state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "question_id": question_id,
        "build": {"status": "pending", "attempts": 0},
        "query": {"status": "pending", "attempts": 0},
    }


def save_state(question_id: str, state: dict[str, Any]) -> None:
    state["updated_at"] = time.time()
    atomic_json(QUESTION_ROOT / question_id / "state.json", state)
    update_progress()


def run_command(command: list[str], cwd: Path, log_path: Path, timeout: int) -> tuple[int | None, float]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        with log_path.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                command,
                cwd=cwd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        return completed.returncode, time.time() - started
    except subprocess.TimeoutExpired:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\n[AUDIT SUPERVISOR] timeout after {timeout} seconds\n")
        return None, time.time() - started


def build_graph(question_id: str, state: dict[str, Any], max_attempts: int) -> bool:
    if valid_graph(question_id):
        state["build"]["status"] = "complete"
        state["build"]["reused"] = question_id in REUSABLE_GRAPHS
        save_state(question_id, state)
        return True

    qdir = QUESTION_ROOT / question_id
    for _ in range(max_attempts):
        attempt = int(state["build"].get("attempts", 0)) + 1
        state["build"].update({"status": "running", "attempts": attempt, "started_at": time.time()})
        save_state(question_id, state)
        ensure_services()

        for iteration in (0, 1):
            partial = GRAPH_ROOT / f"{question_id}_iter_{iteration}"
            if partial.exists() or partial.is_symlink():
                archive_path(partial, question_id, "build", attempt)

        result = qdir / "build/result.json"
        console = qdir / "build/console.log"
        if result.exists():
            archive_path(result, question_id, "build_result", attempt)
        command = [
            str(PYTHON), "-u", str(BUILD_RUNNER),
            "--question-id", question_id,
            "--official-root", str(SOURCE),
            "--memory-dir", str(GRAPH_ROOT),
            "--result-json", str(result),
            "--concurrency", "24",
            "--embedding-batch-size", "16",
            "--text-analysis-max-tokens", "1024",
            "--image-analysis-max-tokens", "1536",
            "--evolution-max-tokens", "1024",
            "--seed", "42",
        ]
        append_event("build_start", question_id=question_id, attempt=attempt)
        return_code, duration = run_command(command, LAB, console, timeout=1800)
        good = return_code == 0 and valid_graph(question_id) and result.exists()
        state["build"].update(
            {
                "status": "complete" if good else "failed",
                "return_code": return_code,
                "duration_seconds": duration,
                "finished_at": time.time(),
            }
        )
        if result.exists():
            try:
                build_result = json.loads(result.read_text(encoding="utf-8"))
                state["build"]["node_count"] = build_result.get("node_count")
                state["build"]["usage"] = compact_usage(build_result.get("usage", {}))
            except Exception as exc:
                state["build"]["result_parse_error"] = str(exc)
        save_state(question_id, state)
        append_event(
            "build_complete" if good else "build_failed",
            question_id=question_id,
            attempt=attempt,
            duration_seconds=duration,
            return_code=return_code,
        )
        if good:
            return True
        if not endpoint_ready(VLM_URL) or not endpoint_ready(EMBED_URL):
            stop_tmux(VLM_SESSION)
            stop_tmux(EMBED_SESSION)
    return False


def prediction_path(question_id: str) -> Path:
    return QUESTION_ROOT / question_id / "qa/local-qwen-vl_dag_rag_1.jsonl"


def valid_query(question_id: str) -> bool:
    qdir = QUESTION_ROOT / question_id / "qa"
    pred = prediction_path(question_id)
    trace = qdir / "logs" / f"data_{question_id}" / "official_trace.jsonl"
    retrieval = qdir / "logs" / f"data_{question_id}" / "retrieval_results.jsonl"
    return all(path.exists() and path.stat().st_size > 0 for path in (pred, trace, retrieval))


def normalize(value: Any) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def compact_usage(usage: Any) -> dict[str, Any]:
    """Keep aggregate telemetry without copying every raw model call into state."""
    if not isinstance(usage, dict):
        return {}
    compact = {
        key: value
        for key, value in usage.items()
        if key in {"prompt_tokens", "completion_tokens", "total_tokens", "embedding_tokens", "by_stage"}
    }
    calls = usage.get("calls")
    if isinstance(calls, list):
        compact["call_count"] = len(calls)
    elif isinstance(calls, (int, float)):
        compact["call_count"] = calls
    return compact


def summarize_prediction(question_id: str) -> dict[str, Any]:
    row = json.loads(prediction_path(question_id).read_text(encoding="utf-8").splitlines()[0])
    prediction = row.get("pred")
    reference = row.get("answer")
    pred_norm = normalize(prediction)
    ref_norm = normalize(reference)
    return {
        "prediction": prediction,
        "reference": reference,
        "raw_response_present": bool(str(row.get("response") or "").strip()),
        "parsed_prediction_present": bool(str(prediction or "").strip()),
        "normalized_exact_match": bool(pred_norm and pred_norm == ref_norm),
        "normalized_reference_contains_prediction": bool(pred_norm and pred_norm in ref_norm),
        "normalized_prediction_contains_reference": bool(ref_norm and ref_norm in pred_norm),
        "process_time": row.get("process_time"),
        "usage": compact_usage(row.get("usage", {})),
    }


def run_query(question_id: str, input_path: Path, state: dict[str, Any], max_attempts: int) -> bool:
    if valid_query(question_id):
        state["query"].update({"status": "complete", **summarize_prediction(question_id)})
        save_state(question_id, state)
        return True

    qdir = QUESTION_ROOT / question_id
    for _ in range(max_attempts):
        attempt = int(state["query"].get("attempts", 0)) + 1
        state["query"].update({"status": "running", "attempts": attempt, "started_at": time.time()})
        save_state(question_id, state)
        ensure_services()
        qa_dir = qdir / "qa"
        if qa_dir.exists():
            archive_path(qa_dir, question_id, "query", attempt)
        command = [
            "bash", str(QA_RUNNER), question_id, str(GRAPH_ROOT), str(qa_dir), str(input_path)
        ]
        append_event("query_start", question_id=question_id, attempt=attempt)
        return_code, duration = run_command(command, LAB, qdir / "qa_console.log", timeout=1800)
        good = return_code == 0 and valid_query(question_id)
        state["query"].update(
            {
                "status": "complete" if good else "failed",
                "return_code": return_code,
                "duration_seconds": duration,
                "finished_at": time.time(),
            }
        )
        if good:
            state["query"].update(summarize_prediction(question_id))
        save_state(question_id, state)
        append_event(
            "query_complete" if good else "query_failed",
            question_id=question_id,
            attempt=attempt,
            duration_seconds=duration,
            return_code=return_code,
        )
        if good:
            return True
        if not endpoint_ready(VLM_URL) or not endpoint_ready(EMBED_URL):
            stop_tmux(VLM_SESSION)
            stop_tmux(EMBED_SESSION)
    return False


def load_rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line]


def update_progress() -> None:
    rows = load_rows()
    states = {}
    for row in rows:
        question_id = str(row["_id"])
        state_path = QUESTION_ROOT / question_id / "state.json"
        states[question_id] = (
            json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else load_state(question_id)
        )
    build_complete = sum(state["build"]["status"] == "complete" for state in states.values())
    query_complete = sum(state["query"]["status"] == "complete" for state in states.values())
    query_failed = sum(state["query"]["status"] == "failed" for state in states.values())
    parsed_missing = sum(
        state["query"]["status"] == "complete" and not state["query"].get("parsed_prediction_present", False)
        for state in states.values()
    )
    exact = sum(state["query"].get("normalized_exact_match", False) for state in states.values())
    progress = {
        "updated_at": time.time(),
        "question_count": len(rows),
        "build_complete": build_complete,
        "query_complete": query_complete,
        "query_failed": query_failed,
        "parsed_prediction_missing": parsed_missing,
        "normalized_exact_match": exact,
        "states": states,
    }
    atomic_json(PROGRESS, progress)
    write_live_report(progress)


def write_live_report(progress: dict[str, Any]) -> None:
    completed = [
        state for state in progress["states"].values() if state["query"]["status"] == "complete"
    ]
    build_times = [
        float(state["build"]["duration_seconds"])
        for state in progress["states"].values()
        if state["build"].get("duration_seconds") is not None
    ]
    query_times = [
        float(state["query"].get("process_time") or state["query"].get("duration_seconds"))
        for state in completed
        if state["query"].get("process_time") is not None or state["query"].get("duration_seconds") is not None
    ]
    suspicious = [
        state for state in completed
        if not state["query"].get("parsed_prediction_present", False)
        or not (
            state["query"].get("normalized_exact_match", False)
            or state["query"].get("normalized_reference_contains_prediction", False)
            or state["query"].get("normalized_prediction_contains_reference", False)
        )
    ]
    lines = [
        "# Resumable 100-Question G2 Failure Audit",
        "",
        "## Scope",
        "",
        "This is the optimized-8B low-resource baseline running the official G2 online",
        "Planning Graph, Worker, sufficiency, refinement, and synthesis path. It is not",
        "silently relabeled as the original 32B baseline. Suspected failures require",
        "trace inspection and, where feasible, teacher validation.",
        "",
        "## Live status",
        "",
        f"- Updated Unix time: `{progress['updated_at']:.3f}`",
        f"- Graphs complete: **{progress['build_complete']}/{progress['question_count']}**",
        f"- Queries complete: **{progress['query_complete']}/{progress['question_count']}**",
        f"- Queries currently failed after retries: **{progress['query_failed']}**",
        f"- Parsed predictions missing: **{progress['parsed_prediction_missing']}**",
        f"- Strict normalized exact matches: **{progress['normalized_exact_match']}**",
        f"- Mean newly built graph time: **{sum(build_times) / len(build_times):.2f} s**" if build_times else "- Mean newly built graph time: pending",
        f"- Mean completed query time: **{sum(query_times) / len(query_times):.2f} s**" if query_times else "- Mean completed query time: pending",
        "",
        "Strict string matching is only a triage signal. Long-form semantic correctness",
        "and failure attribution are determined from the complete traces after execution.",
        "",
        "## Preliminary review queue",
        "",
    ]
    if suspicious:
        lines.extend(
            f"- `{state['question_id']}`: pred={json.dumps(state['query'].get('prediction'), ensure_ascii=False)}; "
            f"reference={json.dumps(state['query'].get('reference'), ensure_ascii=False)}"
            for state in suspicious
        )
    else:
        lines.append("No completed question is currently flagged by the conservative triage rule.")
    lines.extend(
        [
            "",
            "## Durability and recovery",
            "",
            "- `PROGRESS.json` is rewritten atomically after every state transition.",
            "- `journal.jsonl` is append-only.",
            "- Each question has independent build and query checkpoints.",
            "- Failed partial outputs are moved to `failed_attempts/` before retry.",
            "- Local VLM and embedding endpoints are health-checked and restarted.",
            "- Re-running the same command skips every validated graph and query.",
            "",
            "## Next analysis",
            "",
            "After the run, every incorrect or suspicious answer will be classified as",
            "retrieval, Worker-support, decomposition, composition, sufficiency, parser,",
            "infrastructure, or unverifiable, with low-resource confounds recorded separately.",
            "",
        ]
    )
    if FINDINGS.exists():
        lines.extend([FINDINGS.read_text(encoding="utf-8").rstrip(), ""])
    temporary = REPORT.with_suffix(".md.tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(REPORT)


def manifest() -> dict[str, Any]:
    return {
        "name": "optimized_8b_spiqa100_failure_audit_v1",
        "created_at": time.time(),
        "questions": str(QUESTIONS),
        "questions_sha256": hashlib.sha256(QUESTIONS.read_bytes()).hexdigest(),
        "question_count": len(load_rows()),
        "source": str(SOURCE),
        "builder_model": str(VLM_MODEL),
        "online_model": str(VLM_MODEL),
        "embedding_model": str(EMBED_MODEL),
        "seed": 42,
        "top_k": 5,
        "evolution_rounds": 1,
        "document_limit": 5,
        "graph_concurrency": 24,
        "embedding_batch_size": 16,
        "classification_mode": "post-hoc behavior-neutral",
        "attribution_warning": "optimized 8B results are not automatically original 32B G2 failures",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--stop-services", action="store_true")
    args = parser.parse_args()

    ROOT.mkdir(parents=True, exist_ok=True)
    QUESTION_ROOT.mkdir(parents=True, exist_ok=True)
    FAILED_ROOT.mkdir(parents=True, exist_ok=True)
    if not (ROOT / "run_manifest.json").exists():
        atomic_json(ROOT / "run_manifest.json", manifest())
    install_reusable_graphs()
    update_progress()
    ensure_services()

    rows = load_rows()
    if args.limit is not None:
        rows = rows[: args.limit]
    for position, row in enumerate(rows, start=1):
        question_id = str(row["_id"])
        qdir = QUESTION_ROOT / question_id
        qdir.mkdir(parents=True, exist_ok=True)
        input_path = qdir / "input.jsonl"
        if not input_path.exists():
            input_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        state = load_state(question_id)
        state["position"] = position
        save_state(question_id, state)
        if not build_graph(question_id, state, args.max_attempts):
            append_event("question_blocked", question_id=question_id, stage="build")
            continue
        if not run_query(question_id, input_path, state, args.max_attempts):
            append_event("question_blocked", question_id=question_id, stage="query")
            continue
        append_event("question_complete", question_id=question_id, position=position)

    update_progress()
    append_event("run_pass_complete", processed=len(rows))
    if args.stop_services:
        stop_tmux(VLM_SESSION)
        stop_tmux(EMBED_SESSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

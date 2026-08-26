#!/usr/bin/env python3
"""Adjudicate completed matched-32B replays without changing replay outputs.

The replay runner uses the same optimized-8B Content Graph for both readers.
This script therefore measures reader-side changes only.  It records official
parser success separately from semantic correctness of an explicitly tagged
raw answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from semantic_adjudicate import atomic_json, request_judgment


ROOT = Path(__file__).resolve().parent
PROGRESS = ROOT / "REPLAY_PROGRESS.json"
OUTCOMES = ROOT / "OUTCOMES.jsonl"
CAUSAL = ROOT / "CAUSAL_SUMMARY.json"
RESULTS = ROOT / "replay_semantic_results"
SUMMARY = ROOT / "REPLAY_ADJUDICATION.json"
REPORT = ROOT / "REPLAY_ADJUDICATION.md"


def recover_open_output(response: str) -> str | None:
    """Recover only an explicit unclosed output tag for derived analysis."""
    if "<output>" not in response or "</output>" in response:
        return None
    candidate = response.rsplit("<output>", 1)[1].strip()
    return candidate or None


def prediction_path(question_id: str, state: dict[str, Any]) -> Path:
    output_dir = Path(state.get("output_dir") or ROOT / "teacher_replays" / question_id)
    return output_dir / "local-qwen-vl_dag_rag_1.jsonl"


def load_maps() -> tuple[dict[str, Any], dict[str, Any]]:
    outcomes = {
        row["question_id"]: row
        for row in (
            json.loads(line)
            for line in OUTCOMES.read_text(encoding="utf-8").splitlines()
            if line
        )
    }
    causal_summary = json.loads(CAUSAL.read_text(encoding="utf-8"))
    causal = {
        row["question_id"]: row.get("classification", {})
        for row in causal_summary["results"]
    }
    return outcomes, causal


def adjudicate(question_id: str, state: dict[str, Any], outcomes: dict[str, Any], causal: dict[str, Any]) -> dict[str, Any]:
    target = RESULTS / f"{question_id}.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing

    path = prediction_path(question_id, state)
    if not path.exists() or not path.stat().st_size:
        return {
            "question_id": question_id,
            "status": "not_available",
            "replay_status": state.get("status"),
            "prediction_file": str(path),
        }

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    raw = str(row.get("response") or "")
    official = row.get("pred")
    recovered = recover_open_output(raw) if not official else None
    candidate = official or recovered
    source = (
        "official_parser" if official else
        "derived_unclosed_output_tag" if recovered else
        "no_candidate_answer"
    )
    base = {
        "question_id": question_id,
        "question": row.get("question") or outcomes.get(question_id, {}).get("question"),
        "reference": row.get("answer") or outcomes.get(question_id, {}).get("reference"),
        "candidate_answer": candidate,
        "candidate_source": source,
    }
    if candidate:
        judgment = request_judgment(base)
    else:
        judgment = {
            "question_id": question_id,
            "status": "complete",
            "judgment": {
                "label": "incorrect",
                "confidence": 1.0,
                "rationale": "The matched 32B replay produced no candidate answer.",
            },
            "usage": {},
        }
    result = {
        **judgment,
        "question_id": question_id,
        "official_prediction": official,
        "candidate_answer": candidate,
        "candidate_source": source,
        "official_parser_success": bool(official),
        "has_open_output_tag": "<output>" in raw,
        "has_close_output_tag": "</output>" in raw,
        "prediction_file": str(path),
        "process_time": row.get("process_time"),
        "eight_b_candidate": outcomes.get(question_id, {}).get("candidate_answer"),
        "eight_b_candidate_source": outcomes.get(question_id, {}).get("candidate_source"),
        "eight_b_answer_verdict": causal.get(question_id, {}).get("answer_verdict"),
        "eight_b_primary_category": causal.get(question_id, {}).get("primary_category"),
    }
    atomic_json(target, result)
    return result


def consolidate(results: list[dict[str, Any]], progress: dict[str, Any]) -> None:
    completed = [row for row in results if row.get("status") == "complete"]
    correct = [row for row in completed if row.get("judgment", {}).get("label") == "correct"]
    parsed = [row for row in completed if row.get("official_parser_success")]
    repaired = [
        row for row in correct
        if row.get("eight_b_answer_verdict") != "correct"
    ]
    regressed = [
        row for row in completed
        if row.get("eight_b_answer_verdict") == "correct"
        and row.get("judgment", {}).get("label") != "correct"
    ]
    summary = {
        "target_count": len(progress["targets"]),
        "completed_adjudications": len(completed),
        "official_parser_successes": len(parsed),
        "semantic_correct": len(correct),
        "semantic_repairs_over_8b": len(repaired),
        "semantic_regressions_from_8b": len(regressed),
        "results": results,
    }
    atomic_json(SUMMARY, summary)

    lines = [
        "# Matched 32B Reader Replay Adjudication",
        "",
        "The Content Graph is held fixed to the optimized-8B graph. Only the",
        "online reader changes from Qwen3-VL-8B to Qwen3-VL-32B, so these",
        "comparisons isolate reader/model sensitivity; they do not measure graph",
        "construction quality or an end-to-end original-32B baseline.",
        "",
        f"- Replay targets: **{len(progress['targets'])}**",
        f"- Completed semantic adjudications: **{len(completed)}**",
        f"- Official parser successes: **{len(parsed)}/{len(completed)}**",
        f"- Semantically correct raw/candidate answers: **{len(correct)}/{len(completed)}**",
        f"- 8B incorrect to 32B correct: **{len(repaired)}**",
        f"- 8B correct to 32B incorrect: **{len(regressed)}**",
        "",
        "| Question | 8B category | 8B verdict | 32B parsed | 32B semantic | Time (s) |",
        "|---|---|---|---:|---|---:|",
    ]
    by_id = {row["question_id"]: row for row in results}
    for question_id in progress["targets"]:
        row = by_id.get(question_id, {})
        label = row.get("judgment", {}).get("label", row.get("status", "pending"))
        elapsed = row.get("process_time")
        elapsed_text = f"{elapsed:.2f}" if isinstance(elapsed, (int, float)) else "-"
        lines.append(
            f"| `{question_id}` | `{row.get('eight_b_primary_category', '-')}` | "
            f"`{row.get('eight_b_answer_verdict', '-')}` | "
            f"{'yes' if row.get('official_parser_success') else 'no'} | "
            f"`{label}` | {elapsed_text} |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    outcomes, causal = load_maps()
    RESULTS.mkdir(parents=True, exist_ok=True)
    results = [
        adjudicate(question_id, progress["states"].get(question_id, {}), outcomes, causal)
        for question_id in progress["targets"]
    ]
    consolidate(results, progress)


if __name__ == "__main__":
    main()

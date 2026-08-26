#!/usr/bin/env python3
"""Create behavior-neutral audit telemetry from completed official G2 traces.

This deliberately does not assign causal failure categories. It produces a
review queue and measurable trace facts; causal labels require inspecting the
retrieved evidence, Worker output, Planning Graph, and final synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROGRESS = ROOT / "PROGRESS.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def summarize(question_id: str, state: dict[str, Any]) -> dict[str, Any]:
    trace_path = ROOT / "questions" / question_id / "qa" / "logs" / f"data_{question_id}" / "official_trace.jsonl"
    events = read_jsonl(trace_path)
    planning = [event for event in events if event.get("event") == "planning_execution"]
    workers = [event for event in events if event.get("event") == "worker_result"]
    checks = [event for event in events if event.get("event") == "evidence_check"]
    calls = [event for event in events if event.get("event") == "model_call"]
    endings = [event for event in events if event.get("event") == "question_end"]
    rounds = [int(event.get("round", 0)) for event in planning + checks if event.get("round") is not None]
    parser_signals = sum(event.get("parsed") is False for event in checks)
    insufficient = sum(event.get("sufficient") is False for event in checks)
    model_errors = sum(event.get("status") not in (None, "ok", "success") for event in calls)
    query = state.get("query", {})
    flags = []
    if not query.get("parsed_prediction_present", False):
        flags.append("missing_final_parse")
    if not (
        query.get("normalized_exact_match", False)
        or query.get("normalized_reference_contains_prediction", False)
        or query.get("normalized_prediction_contains_reference", False)
    ):
        flags.append("lexical_or_semantic_review")
    if parser_signals:
        flags.append("intermediate_parser_signal")
    if max(rounds, default=0) >= 2:
        flags.append("multiple_refinement_rounds")
    if model_errors:
        flags.append("model_call_error")
    return {
        "question_id": question_id,
        "prediction": query.get("prediction"),
        "reference": query.get("reference"),
        "query_seconds": query.get("process_time") or query.get("duration_seconds"),
        "planning_executions": len(planning),
        "maximum_round": max(rounds, default=0),
        "worker_results": len(workers),
        "evidence_checks": len(checks),
        "unparsed_evidence_checks": parser_signals,
        "insufficient_evidence_checks": insufficient,
        "online_model_calls": len(calls),
        "online_model_call_errors": model_errors,
        "question_end_events": len(endings),
        "review_flags": flags,
        "trace": str(trace_path),
    }


def main() -> None:
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    rows = [
        summarize(question_id, state)
        for question_id, state in progress["states"].items()
        if state.get("query", {}).get("status") == "complete"
    ]
    output = {
        "scope": "behavior-neutral trace telemetry; not causal failure labels",
        "completed": len(rows),
        "review_queue_size": sum(bool(row["review_flags"]) for row in rows),
        "questions": rows,
    }
    (ROOT / "TRACE_SUMMARY.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Trace Review Queue",
        "",
        "These are behavior-neutral signals, not final causal classifications.",
        "A flagged case must be reviewed against its retrieved nodes and trace.",
        "",
        f"- Completed traces summarized: **{len(rows)}**",
        f"- Questions with one or more review signals: **{output['review_queue_size']}**",
        "",
        "| Question | Pred / reference | Rounds | Workers | Calls | Check parse failures | Signals |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        pred_ref = f"{row['prediction']} / {row['reference']}".replace("|", "\\|").replace("\n", " ")
        flags = ", ".join(row["review_flags"]) or "none"
        lines.append(
            f"| `{row['question_id']}` | {pred_ref} | {row['maximum_round']} | "
            f"{row['worker_results']} | {row['online_model_calls']} | "
            f"{row['unparsed_evidence_checks']} | {flags} |"
        )
    (ROOT / "TRACE_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

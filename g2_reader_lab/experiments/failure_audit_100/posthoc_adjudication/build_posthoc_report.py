#!/usr/bin/env python3
"""Consolidate execution, semantic, causal, integrity, and replay findings."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT.parent


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    outcomes = {row["question_id"]: row for row in read_jsonl(ROOT / "OUTCOMES.jsonl")}
    semantic_data = json.loads((ROOT / "SEMANTIC_SUMMARY.json").read_text(encoding="utf-8"))
    semantic = {row["question_id"]: row for row in semantic_data["results"]}
    causal_data = json.loads((ROOT / "CAUSAL_SUMMARY.json").read_text(encoding="utf-8"))
    causal = {row["question_id"]: row for row in causal_data["results"]}
    visual = {}
    visual_path = ROOT / "visual_validation/VISUAL_VALIDATION.json"
    if visual_path.exists():
        visual_data = json.loads(visual_path.read_text(encoding="utf-8"))
        visual = {row["question_id"]: row for row in visual_data["results"]}
    progress = json.loads((AUDIT / "PROGRESS.json").read_text(encoding="utf-8"))
    invalid = {question_id for question_id, row in causal.items() if row["classification"]["primary_category"] == "dataset_failure"}
    invalid.update(
        question_id for question_id, row in visual.items()
        if row["final_category"] == "dataset_failure"
    )
    valid_ids = set(progress["states"]) - invalid

    final_verdict = {}
    for question_id in valid_ids:
        if question_id in causal:
            final_verdict[question_id] = causal[question_id]["classification"]["answer_verdict"]
        elif question_id in semantic:
            final_verdict[question_id] = semantic[question_id]["judgment"]["label"]
        else:
            final_verdict[question_id] = "incorrect"
        visual_verdict = visual.get(question_id, {}).get("answer_verdict")
        if visual_verdict in {"correct", "incorrect", "ambiguous"}:
            final_verdict[question_id] = visual_verdict

    official_correct = [
        question_id for question_id in valid_ids
        if final_verdict[question_id] == "correct"
        and outcomes.get(question_id, {}).get("candidate_source") == "official_parser"
    ]
    raw_recovered_correct = [
        question_id for question_id in valid_ids
        if final_verdict[question_id] == "correct"
        and outcomes.get(question_id, {}).get("candidate_source") == "derived_unclosed_output_tag"
    ]
    incorrect = [question_id for question_id in valid_ids if final_verdict[question_id] == "incorrect"]
    ambiguous = [question_id for question_id in valid_ids if final_verdict[question_id] == "ambiguous"]

    primary_counts = {}
    category_ids = {}
    for question_id, row in causal.items():
        category = visual.get(question_id, {}).get(
            "final_category", row["classification"]["primary_category"]
        )
        if question_id in invalid or category == "no_failure":
            continue
        primary_counts[category] = primary_counts.get(category, 0) + 1
        category_ids.setdefault(category, []).append(question_id)

    visual_review_original = [
        question_id for question_id, row in causal.items()
        if question_id not in invalid and row["classification"].get("requires_raw_visual_review")
    ]
    visual_review_remaining = [question_id for question_id in visual_review_original if question_id not in visual]
    worker_ids = category_ids.get("worker_support_failure", [])
    worker_table_numeric = sum(
        any(term in (
            causal.get(question_id, {}).get("classification", {}).get("rationale", "")
            + " " + visual.get(question_id, {}).get("finding", "")
        ).lower() for term in (
            "table", "value", "number", "ratio", "percentage", "score", "auc", "accuracy", "trend", "figure"
        ))
        for question_id in worker_ids
    )

    replay_progress = {}
    replay_path = ROOT / "REPLAY_PROGRESS.json"
    if replay_path.exists():
        replay_progress = json.loads(replay_path.read_text(encoding="utf-8"))
    replay_states = replay_progress.get("states", {})
    replay_complete = sum(row.get("status") == "complete" for row in replay_states.values())
    replay_failed = sum(row.get("status") == "failed" for row in replay_states.values())
    replay_running = [question_id for question_id, row in replay_states.items() if row.get("status") == "running"]
    replay_total = len(replay_states)
    replay_finished = bool(replay_total and replay_complete + replay_failed == replay_total)
    replay_adjudication = None
    replay_adjudication_path = ROOT / "REPLAY_ADJUDICATION.json"
    if replay_adjudication_path.exists():
        replay_adjudication = json.loads(replay_adjudication_path.read_text(encoding="utf-8"))

    lines = [
        "# SPIQA-100 G2 Failure Audit: Post-Hoc Report",
        "",
        "## Current conclusion",
        "",
        "The execution pass, semantic/trace adjudication, and raw visual validation are complete.",
        ("Targeted matched-32B replay is complete." if replay_finished else
         "Targeted matched-32B replay is still in progress."),
        "Counts below describe the optimized-8B configuration. Matched 32B replay",
        "separates some reader-model sensitivity, but this is not an end-to-end",
        "original-32B baseline.",
        "",
        "## Data integrity",
        "",
        f"- Requested slice: **{len(progress['states'])}** questions",
        f"- Invalid benchmark rows excluded: **{len(invalid)}** ({', '.join(sorted(invalid))})",
        f"- Valid denominator: **{len(valid_ids)}**",
        "",
        "## Answer outcomes after cross-validation",
        "",
        f"- Officially parsed and semantically correct: **{len(official_correct)}/{len(valid_ids)}**",
        f"- Additional semantically correct raw answers lost by parser: **{len(raw_recovered_correct)}**",
        f"- Raw/candidate answer correctness: **{len(official_correct) + len(raw_recovered_correct)}/{len(valid_ids)}**",
        f"- Incorrect or no-answer outcomes: **{len(incorrect)}**",
        f"- Ambiguous valid outcomes: **{len(ambiguous)}**",
        "",
        "The semantic screen used structured Qwen3-VL-32B adjudication. Suspected",
        "errors then received a second evidence-backed trace judgment, which corrected",
        "12 over-strict reference-matching false positives plus one recovered-output case.",
        "",
        "## Primary failure categories",
        "",
    ]
    for category, count in sorted(primary_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{category}`: **{count}** — {', '.join(f'`{qid}`' for qid in sorted(category_ids[category]))}")
    lines.extend(
        [
            "",
            "## Dominant repair signal",
            "",
            f"Worker-support failures remain the largest class (**{len(worker_ids)}**).",
            f"A conservative keyword screen finds table/figure/value/trend language in **{worker_table_numeric}/{len(worker_ids)}**",
            "classification rationales. This supports—but does not yet finalize—the",
            "planned evidence-node citation, value/unit verification, deterministic",
            "calculation, and local Worker repair experiment.",
            "",
            "## Required validation",
            "",
            f"- Raw visual cases completed: **{len(visual)}/12**",
            f"- Raw visual cases still unresolved: **{len(visual_review_remaining)}**"
            + ((" — " + ", ".join(f"`{qid}`" for qid in sorted(visual_review_remaining))) if visual_review_remaining else ""),
            f"- Targeted 32B replays complete: **{replay_complete}/{replay_total}**",
            f"- Targeted 32B replays failed: **{replay_failed}**",
            f"- Replay currently running: **{', '.join(replay_running) if replay_running else 'none'}**",
            "- `spiqa_96` separately reproduced its malformed Planning Graph JSON with",
            "  the 32B reader on all 15 official retries.",
        ]
    )
    if replay_adjudication:
        adjudicated = replay_adjudication["completed_adjudications"]
        lines.extend([
            "",
            "## Matched-reader result",
            "",
            f"- Replays semantically adjudicated: **{adjudicated}/{replay_total}**",
            f"- Official parser successes: **{replay_adjudication['official_parser_successes']}/{adjudicated}**",
            f"- Semantically correct 32B answers: **{replay_adjudication['semantic_correct']}/{adjudicated}**",
            f"- 8B-incorrect cases repaired by 32B: **{replay_adjudication['semantic_repairs_over_8b']}**",
            f"- 8B-correct cases regressed under 32B: **{replay_adjudication['semantic_regressions_from_8b']}**",
            "",
            "These matched replays hold the Content Graph fixed, so they isolate",
            "reader/model sensitivity rather than graph-construction quality.",
        ])
    if visual:
        lines.extend([
            "",
            "## Raw visual validation result",
            "",
            "- Two provisional errors (`spiqa_163`, `spiqa_215`) were restored as correct.",
            "- Four cases (`spiqa_164`, `spiqa_195`, `spiqa_281`, `spiqa_452`)",
            "  were excluded because the benchmark question/reference conflicts with the source.",
            "- `spiqa_368` moved from retrieval to Worker support; `spiqa_578` moved",
            "  from Worker support to retrieval; `spiqa_98` moved from parser-only",
            "  to Worker support with parser as secondary.",
            "- The four new dataset-failure decisions should receive independent",
            "  human confirmation before publication.",
        ])
    lines.extend([
        "",
        "## Artifacts",
        "",
        "- `OUTCOMES.jsonl`: immutable-source outcome inventory",
        "- `PARSER_RECOVERY.md`: derived unclosed-output recovery",
        "- `SEMANTIC_ADJUDICATION.md`: first-pass semantic judgments",
        "- `CAUSAL_CLASSIFICATION.md`: evidence-backed causal judgments",
        "- `DATA_INTEGRITY.md`: invalid-row and matched parser findings",
        "- `REPLAY_ADJUDICATION.md`: matched 32B reader comparison",
        "- `visual_validation/VISUAL_VALIDATION.md`: source-grounded raw-image review",
        "- `teacher_replays/`: matched 32B reader outputs on identical 8B graphs",
        "",
    ])
    (ROOT / "POSTHOC_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

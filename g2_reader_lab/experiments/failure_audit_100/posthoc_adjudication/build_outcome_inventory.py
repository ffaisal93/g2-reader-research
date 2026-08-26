#!/usr/bin/env python3
"""Build a derived outcome inventory without changing frozen G2 outputs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


AUDIT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parent
PROGRESS = AUDIT / "PROGRESS.json"


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def recover_open_output(response: str) -> str | None:
    """Recover only an explicit unclosed <output>; never infer from thought text."""
    if "<output>" not in response or "</output>" in response:
        return None
    candidate = response.rsplit("<output>", 1)[1].strip()
    return candidate or None


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    outcomes = []
    recovery_rows = []
    for question_id, state in progress["states"].items():
        query = state.get("query", {})
        if query.get("status") != "complete":
            continue
        prediction_file = AUDIT / "questions" / question_id / "qa" / "local-qwen-vl_dag_rag_1.jsonl"
        row = json.loads(prediction_file.read_text(encoding="utf-8").splitlines()[0])
        raw = str(row.get("response") or "")
        official = row.get("pred")
        recovered = recover_open_output(raw) if not official else None
        candidate = official if official else recovered
        if official:
            source = "official_parser"
        elif recovered:
            source = "derived_unclosed_output_tag"
        else:
            source = "no_candidate_answer"
        reference = row.get("answer")
        pred_norm, ref_norm = normalize(candidate), normalize(reference)
        outcome = {
            "question_id": question_id,
            "question": row.get("question"),
            "reference": reference,
            "official_prediction": official,
            "candidate_answer": candidate,
            "candidate_source": source,
            "raw_response_present": bool(raw.strip()),
            "has_open_output_tag": "<output>" in raw,
            "has_close_output_tag": "</output>" in raw,
            "raw_response_characters": len(raw),
            "normalized_exact_match": bool(pred_norm and pred_norm == ref_norm),
            "normalized_containment_match": bool(
                pred_norm and ref_norm and (pred_norm in ref_norm or ref_norm in pred_norm)
            ),
            "prediction_file": str(prediction_file),
            "prediction_file_sha256": hashlib.sha256(prediction_file.read_bytes()).hexdigest(),
        }
        outcomes.append(outcome)
        if not official:
            recovery_rows.append(outcome)

    with (ROOT / "OUTCOMES.jsonl").open("w", encoding="utf-8") as handle:
        for outcome in outcomes:
            handle.write(json.dumps(outcome, ensure_ascii=False) + "\n")
    counts = {
        "completed_outputs": len(outcomes),
        "official_predictions": sum(row["candidate_source"] == "official_parser" for row in outcomes),
        "recovered_unclosed_output_tags": sum(
            row["candidate_source"] == "derived_unclosed_output_tag" for row in outcomes
        ),
        "no_candidate_answer": sum(row["candidate_source"] == "no_candidate_answer" for row in outcomes),
    }
    (ROOT / "OUTCOME_COUNTS.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Parser Recovery Inventory",
        "",
        "Original G2 outputs are immutable. Recovery is recorded only in derived",
        "artifacts and only when an explicit `<output>` tag lacks its closing tag.",
        "Thought text is never silently promoted to an answer.",
        "",
        f"- Completed query outputs: **{counts['completed_outputs']}**",
        f"- Officially parsed predictions: **{counts['official_predictions']}**",
        f"- Explicit unclosed outputs recovered: **{counts['recovered_unclosed_output_tags']}**",
        f"- No candidate answer recoverable: **{counts['no_candidate_answer']}**",
        "",
        "| Question | Derived status | Recovered candidate | Reference |",
        "|---|---|---|---|",
    ]
    for row in recovery_rows:
        candidate = str(row["candidate_answer"] or "").replace("|", "\\|").replace("\n", " ")
        reference = str(row["reference"] or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{row['question_id']}` | `{row['candidate_source']}` | {candidate} | {reference} |"
        )
    (ROOT / "PARSER_RECOVERY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

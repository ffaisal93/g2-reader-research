#!/usr/bin/env python3
"""Idempotent 32B semantic equivalence adjudication for derived outcomes."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTCOMES = ROOT / "OUTCOMES.jsonl"
RESULTS = ROOT / "semantic_results"
SUMMARY = ROOT / "SEMANTIC_SUMMARY.json"
REPORT = ROOT / "SEMANTIC_ADJUDICATION.md"
ENDPOINT = "http://127.0.0.1:18000/v1/chat/completions"

SCHEMA = {
    "name": "semantic_answer_judgment",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": ["correct", "incorrect", "ambiguous"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reference_claims": {"type": "array", "items": {"type": "string"}},
            "candidate_claims": {"type": "array", "items": {"type": "string"}},
            "substantive_differences": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
        },
        "required": [
            "label", "confidence", "reference_claims", "candidate_claims",
            "substantive_differences", "rationale"
        ],
        "additionalProperties": False,
    },
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def request_judgment(row: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
    prompt = f"""Judge semantic correctness of a candidate answer against a benchmark reference.

Question:
{row['question']}

Reference answer:
{row['reference']}

Candidate answer:
{row['candidate_answer']}

Rules:
- Mark correct when the candidate answers the central question with the same factual meaning. Paraphrases and harmless extra detail are allowed.
- Mark incorrect for a wrong entity, value, comparison, trend, calculation, missing required component, or contradiction.
- Mark ambiguous only when equivalence genuinely cannot be decided from the question and answers alone.
- Do not assume the candidate is correct merely because it is fluent.
- Treat the reference as the benchmark target for this semantic-equivalence stage.
Return concise structured analysis."""
    payload = {
        "model": "local-qwen-vl",
        "messages": [
            {"role": "system", "content": "You are a strict scientific QA evaluator."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 700,
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }
    body = json.dumps(payload).encode("utf-8")
    last_error = ""
    for attempt in range(1, attempts + 1):
        started = time.time()
        try:
            request = urllib.request.Request(
                ENDPOINT, data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer local"}
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                envelope = json.loads(response.read().decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
            judgment = json.loads(content)
            return {
                "question_id": row["question_id"],
                "candidate_source": row["candidate_source"],
                "candidate_answer": row["candidate_answer"],
                "reference": row["reference"],
                "status": "complete",
                "attempt": attempt,
                "latency_seconds": time.time() - started,
                "judgment": judgment,
                "usage": envelope.get("usage", {}),
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(attempt * 2)
    return {
        "question_id": row["question_id"],
        "candidate_source": row["candidate_source"],
        "candidate_answer": row["candidate_answer"],
        "reference": row["reference"],
        "status": "failed",
        "error": last_error,
    }


def process(row: dict[str, Any]) -> dict[str, Any]:
    target = RESULTS / f"{row['question_id']}.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return existing
    if not row.get("candidate_answer"):
        result = {
            "question_id": row["question_id"],
            "candidate_source": row["candidate_source"],
            "candidate_answer": None,
            "reference": row["reference"],
            "status": "complete",
            "judgment": {
                "label": "incorrect",
                "confidence": 1.0,
                "reference_claims": [],
                "candidate_claims": [],
                "substantive_differences": ["No candidate answer was produced."],
                "rationale": "No answer is available for semantic comparison.",
            },
            "usage": {},
        }
    else:
        result = request_judgment(row)
    atomic_json(target, result)
    return result


def consolidate(rows: list[dict[str, Any]]) -> None:
    labels = {"correct": 0, "incorrect": 0, "ambiguous": 0, "failed": 0}
    for result in rows:
        if result.get("status") != "complete":
            labels["failed"] += 1
        else:
            labels[result["judgment"]["label"]] += 1
    summary = {"completed_outputs": len(rows), "counts": labels, "results": rows}
    atomic_json(SUMMARY, summary)
    lines = [
        "# Semantic Adjudication",
        "",
        "This is a 32B structured-output semantic-equivalence screen. It does not",
        "replace evidence-based causal classification or human review of ambiguous",
        "and low-confidence cases.",
        "",
        f"- Correct: **{labels['correct']}**",
        f"- Incorrect: **{labels['incorrect']}**",
        f"- Ambiguous: **{labels['ambiguous']}**",
        f"- Adjudication request failures: **{labels['failed']}**",
        "",
        "| Question | Source | Label | Confidence | Rationale |",
        "|---|---|---|---:|---|",
    ]
    for result in rows:
        judgment = result.get("judgment", {})
        rationale = str(judgment.get("rationale") or result.get("error") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{result['question_id']}` | `{result['candidate_source']}` | "
            f"`{judgment.get('label', 'failed')}` | {judgment.get('confidence', 0):.2f} | {rationale} |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    rows = [json.loads(line) for line in OUTCOMES.read_text(encoding="utf-8").splitlines() if line]
    if args.limit is not None:
        rows = rows[: args.limit]
    RESULTS.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(process, rows))
    consolidate(results)


if __name__ == "__main__":
    main()

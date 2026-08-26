#!/usr/bin/env python3
"""Evidence-backed, resumable causal classification of audit failures."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT.parent
SEMANTIC = ROOT / "SEMANTIC_SUMMARY.json"
OUTCOMES = ROOT / "OUTCOMES.jsonl"
PROGRESS = AUDIT / "PROGRESS.json"
RESULTS = ROOT / "causal_results"
SUMMARY = ROOT / "CAUSAL_SUMMARY.json"
REPORT = ROOT / "CAUSAL_CLASSIFICATION.md"
ENDPOINT = "http://127.0.0.1:18000/v1/chat/completions"

CATEGORIES = [
    "retrieval_failure", "worker_support_failure", "decomposition_failure",
    "composition_failure", "sufficiency_failure", "parser_failure",
    "unverifiable", "infrastructure_failure", "mixed", "no_failure",
    "dataset_failure"
]

SCHEMA = {
    "name": "g2_failure_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answer_verdict": {"type": "string", "enum": ["correct", "incorrect", "ambiguous"]},
            "reference_mismatch_material": {"type": "boolean"},
            "primary_category": {"type": "string", "enum": CATEGORIES},
            "secondary_categories": {
                "type": "array", "items": {"type": "string", "enum": CATEGORIES}
            },
            "necessary_evidence_retrieved": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "decisive_evidence_node_ids": {"type": "array", "items": {"type": "string"}},
            "planning_adequate": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "worker_answer_supported": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "final_composition_supported": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "sufficiency_behavior": {
                "type": "string",
                "enum": ["appropriate", "premature_stop", "unnecessary_refinement", "parse_failure", "uncertain"]
            },
            "requires_raw_visual_review": {"type": "boolean"},
            "low_resource_confound": {"type": "string", "enum": ["likely", "possible", "unlikely", "unknown"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
        },
        "required": [
            "answer_verdict", "reference_mismatch_material", "primary_category",
            "secondary_categories", "necessary_evidence_retrieved",
            "decisive_evidence_node_ids", "planning_adequate", "worker_answer_supported",
            "final_composition_supported", "sufficiency_behavior", "requires_raw_visual_review",
            "low_resource_confound", "confidence", "rationale"
        ],
        "additionalProperties": False,
    },
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    output = []
    if not path.exists():
        return output
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            output.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return output


def clip(value: Any, limit: int) -> str:
    text = str(value or "").replace("\x00", "")
    return text if len(text) <= limit else text[:limit] + " [...clipped]"


def tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def collect_evidence(retrieval_rows: list[dict[str, Any]], question: str, reference: str) -> list[dict[str, Any]]:
    target_terms = tokens(question) | tokens(reference)
    found: dict[str, dict[str, Any]] = {}
    position = 0
    for row in retrieval_rows:
        query = row.get("query", "")
        containers = [row.get("semantic_retrieval"), row.get("bm25_retrieval"), row.get("results")]
        for container in containers:
            if not isinstance(container, dict):
                continue
            details = container.get("details") or container.get("results")
            if isinstance(details, dict):
                details = details.get("details") or details.get("results")
            if not isinstance(details, list):
                continue
            for item in details:
                if not isinstance(item, dict):
                    continue
                node_id = str(item.get("node_id") or f"unknown-{position}")
                if node_id in found:
                    continue
                text = item.get("text_content") or item.get("content") or ""
                overlap = len(tokens(text) & target_terms)
                found[node_id] = {
                    "node_id": node_id,
                    "type": item.get("type"),
                    "visual": bool(item.get("visual")),
                    "retrieval_query": query,
                    "text": clip(text, 1400),
                    "overlap": overlap,
                    "position": position,
                }
                position += 1
    ranked = sorted(found.values(), key=lambda item: (-item["overlap"], item["position"]))[:18]
    for item in ranked:
        item.pop("overlap", None)
        item.pop("position", None)
    return ranked


def compact_trace(question_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    base = AUDIT / "questions" / question_id / "qa" / "logs" / f"data_{question_id}"
    events = read_jsonl(base / "official_trace.jsonl")
    retrieval = read_jsonl(base / "retrieval_results.jsonl")
    planning = []
    workers = []
    checks = []
    final = None
    for event in events:
        kind = event.get("event")
        if kind == "planning_execution":
            planning.append({
                "round": event.get("round"),
                "nodes": [
                    {"id": node.get("id"), "task": node.get("task"), "children": node.get("children")}
                    for node in event.get("dag", {}).get("nodes", [])
                ],
            })
        elif kind == "worker_result":
            workers.append({
                "round": event.get("round"), "node_id": event.get("node_id"),
                "task": event.get("task"), "response": clip(event.get("response"), 1300)
            })
        elif kind == "evidence_check":
            checks.append({
                "round": event.get("round"), "parsed": event.get("parsed"),
                "sufficient": event.get("sufficient"), "gaps": event.get("gaps"),
                "response": clip(event.get("response"), 700),
            })
        elif kind == "question_end":
            final = {"prediction": event.get("prediction"), "response": clip(event.get("response"), 1800)}
    # Preserve the earliest and latest Worker behavior when refinement creates a large trace.
    if len(workers) > 12:
        workers = workers[:6] + workers[-6:]
    return {
        "question": outcome["question"],
        "reference": outcome["reference"],
        "candidate_answer": outcome["candidate_answer"],
        "candidate_source": outcome["candidate_source"],
        "planning": planning,
        "retrieved_evidence": collect_evidence(retrieval, outcome["question"], outcome["reference"]),
        "worker_results": workers,
        "sufficiency_checks": checks,
        "final": final,
    }


def call_classifier(question_id: str, packet: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
    prompt = """Classify the primary causal failure in this G2 scientific RAG trace.

Definitions:
- retrieval_failure: evidence necessary for the benchmark answer was not retrieved.
- worker_support_failure: necessary evidence was retrieved, but a Worker misread it or produced an unsupported answer.
- decomposition_failure: the Planning Graph omitted or materially misstated a required subproblem.
- composition_failure: supported intermediate answers existed, but a parent/final answer combined them incorrectly.
- sufficiency_failure: the checker stopped despite a visible unresolved gap or drove inappropriate refinement that caused the failure.
- parser_failure: required structured tags/JSON/output parsing failed or generation was truncated before a usable answer.
- unverifiable: decisive visual evidence is too coarse/unreadable in the recorded trace to determine the earlier category.
- infrastructure_failure: service/process failure, not a model reasoning or parser behavior.
- mixed: two causes are inseparable; avoid this when an earliest primary cause is identifiable.

First decide whether the candidate actually answers the question correctly. The
reference may contain optional explanation beyond what the question requires;
omitting optional reference detail is not an error. Conversely, fluent wording
does not excuse a wrong value, entity, comparison, trend, or required component.
If the candidate is correct, use primary_category=no_failure unless an output
parser failure still caused the official prediction to be null.

Use the earliest decisive cause as primary and list later effects as secondary. A retrieved visual node whose supplied text does not expose the needed value may require raw visual review. Do not infer that fluent Worker text is supported. The benchmark reference is provided to identify necessary evidence, not to rewrite history.

Trace packet:
""" + json.dumps(packet, ensure_ascii=False)
    payload = {
        "model": "local-qwen-vl",
        "messages": [
            {"role": "system", "content": "You audit multimodal RAG failures from recorded evidence."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1000,
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
            with urllib.request.urlopen(request, timeout=300) as response:
                envelope = json.loads(response.read().decode("utf-8"))
            judgment = json.loads(envelope["choices"][0]["message"]["content"])
            return {
                "question_id": question_id, "status": "complete", "attempt": attempt,
                "latency_seconds": time.time() - started, "classification": judgment,
                "usage": envelope.get("usage", {}),
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * attempt)
    return {"question_id": question_id, "status": "failed", "error": last_error}


def fixed_parser_result(
    question_id: str,
    rationale: str,
    secondary: list[str] | None = None,
    answer_verdict: str = "incorrect",
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "status": "complete",
        "classification": {
            "answer_verdict": answer_verdict, "reference_mismatch_material": answer_verdict == "incorrect",
            "primary_category": "parser_failure", "secondary_categories": secondary or [],
            "necessary_evidence_retrieved": "uncertain", "decisive_evidence_node_ids": [],
            "planning_adequate": "uncertain", "worker_answer_supported": "uncertain",
            "final_composition_supported": "uncertain", "sufficiency_behavior": "parse_failure",
            "requires_raw_visual_review": False, "low_resource_confound": "likely",
            "confidence": 1.0, "rationale": rationale,
        },
        "usage": {},
    }


def normalize_result(result: dict[str, Any], outcome: dict[str, Any] | None = None) -> dict[str, Any]:
    """Keep primary failure counts consistent with the declared audit protocol."""
    classification = result.get("classification")
    if not isinstance(classification, dict):
        return result
    if result.get("question_id") == "spiqa_79":
        classification.update(
            {
                "answer_verdict": "ambiguous",
                "reference_mismatch_material": True,
                "primary_category": "dataset_failure",
                "secondary_categories": ["parser_failure"],
                "necessary_evidence_retrieved": "uncertain",
                "planning_adequate": "uncertain",
                "worker_answer_supported": "uncertain",
                "final_composition_supported": "uncertain",
                "sufficiency_behavior": "uncertain",
                "requires_raw_visual_review": False,
                "low_resource_confound": "unknown",
                "confidence": 1.0,
                "rationale": (
                    "The benchmark question is literally 'New question:' while the reference describes "
                    "alpha and recommendation accuracy. This malformed row is excluded from valid G2 "
                    "failure and accuracy denominators."
                ),
            }
        )
        return result
    if (
        outcome is not None
        and classification.get("answer_verdict") == "correct"
    ):
        expected = "no_failure" if outcome.get("candidate_source") == "official_parser" else "parser_failure"
        if classification.get("primary_category") != expected:
            classification["grounding_warning_category"] = classification["primary_category"]
            classification["primary_category"] = expected
            classification["rationale"] = (
                classification.get("rationale", "")
                + " [Audit normalization: the answer is correct; official-parser status determines "
                  "whether this is no primary answer failure or a parser failure. Any grounding concern "
                  "is retained separately.]"
            )
    return result


def process(item: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    outcome, semantic = item
    question_id = outcome["question_id"]
    target = RESULTS / f"{question_id}.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            normalized = normalize_result(existing, outcome)
            atomic_json(target, normalized)
            return normalized
    if outcome["candidate_source"] == "derived_unclosed_output_tag" and semantic["judgment"]["label"] == "correct":
        result = fixed_parser_result(
            question_id,
            "The raw answer is semantically correct, but the explicit <output> tag lacks </output>, so the official parser returned null.",
            answer_verdict="correct",
        )
    else:
        result = call_classifier(question_id, compact_trace(question_id, outcome))
        if outcome["candidate_source"] != "official_parser" and result.get("status") == "complete":
            secondary = result["classification"]["secondary_categories"]
            if result["classification"]["primary_category"] != "parser_failure" and "parser_failure" not in secondary:
                secondary.append("parser_failure")
    result = normalize_result(result, outcome)
    atomic_json(target, result)
    return result


def consolidate(results: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    failed = 0
    for result in results:
        if result.get("status") != "complete":
            failed += 1
            continue
        category = result["classification"]["primary_category"]
        counts[category] = counts.get(category, 0) + 1
    summary = {"classified_cases": len(results), "request_failures": failed, "primary_counts": counts, "results": results}
    atomic_json(SUMMARY, summary)
    lines = [
        "# Causal Failure Classification",
        "",
        "This is evidence-backed 32B trace adjudication plus deterministic parser",
        "labels. Low-confidence and visual-dependent cases require final human/teacher",
        "validation before being reported as intrinsic G2 failures.",
        "",
        f"- Cases classified: **{len(results)}**",
        f"- Classification request failures: **{failed}**",
        "",
        "## Primary counts",
        "",
    ]
    lines.extend(f"- `{category}`: **{count}**" for category, count in sorted(counts.items()))
    lines.extend(["", "| Question | Primary | Confidence | Visual review | Low-resource confound | Rationale |", "|---|---|---:|---|---|---|"])
    for result in results:
        classification = result.get("classification", {})
        rationale = str(classification.get("rationale") or result.get("error") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{result['question_id']}` | `{classification.get('primary_category', 'failed')}` | "
            f"{classification.get('confidence', 0):.2f} | {classification.get('requires_raw_visual_review')} | "
            f"`{classification.get('low_resource_confound', 'unknown')}` | {rationale} |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    outcomes = {row["question_id"]: row for row in read_jsonl(OUTCOMES)}
    semantic_summary = json.loads(SEMANTIC.read_text(encoding="utf-8"))
    semantic = {row["question_id"]: row for row in semantic_summary["results"]}
    cases = []
    for question_id, result in semantic.items():
        outcome = outcomes[question_id]
        if result["judgment"]["label"] == "incorrect" or outcome["candidate_source"] != "official_parser":
            cases.append((outcome, result))

    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    fixed = []
    for question_id, state in progress["states"].items():
        if state.get("query", {}).get("status") != "failed":
            continue
        target = RESULTS / f"{question_id}.json"
        result = fixed_parser_result(
            question_id,
            "Planning Graph generation exhausted all retries because every structured JSON response was malformed; Worker execution never began."
        )
        result = normalize_result(result)
        atomic_json(target, result)
        fixed.append(result)
    if args.limit is not None:
        cases = cases[: args.limit]
    RESULTS.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        classified = list(executor.map(process, cases))
    consolidate(fixed + classified)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Materialize compact evidence packets for every trace-review candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PACKETS = ROOT / "review_packets"


def jsonl(path: Path) -> list[dict[str, Any]]:
    output = []
    if not path.exists():
        return output
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            output.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return output


def clipped(value: Any, limit: int = 6000) -> str:
    text = str(value or "").replace("\x00", "")
    return text if len(text) <= limit else text[:limit] + "\n[...clipped...]"


def retrieval_details(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for container in (row.get("semantic_retrieval"), row.get("bm25_retrieval"), row.get("results")):
        if not isinstance(container, dict):
            continue
        details = container.get("details") or container.get("results")
        if isinstance(details, dict):
            details = details.get("details") or details.get("results")
        if isinstance(details, list):
            candidates.extend(item for item in details if isinstance(item, dict))
    return candidates


def make_packet(summary: dict[str, Any]) -> str:
    question_id = summary["question_id"]
    base = ROOT / "questions" / question_id / "qa" / "logs" / f"data_{question_id}"
    events = jsonl(base / "official_trace.jsonl")
    retrievals = jsonl(base / "retrieval_results.jsonl")
    starts = [event for event in events if event.get("event") == "question_start"]
    question = starts[0].get("question") if starts else ""
    lines = [
        f"# Review packet: `{question_id}`",
        "",
        f"- Question: {question}",
        f"- Prediction: `{summary.get('prediction')}`",
        f"- Reference: `{summary.get('reference')}`",
        f"- Review signals: `{', '.join(summary.get('review_flags', []))}`",
        f"- Maximum refinement round: `{summary.get('maximum_round')}`",
        "",
        "## Planning Graphs",
        "",
    ]
    for event in events:
        if event.get("event") != "planning_execution":
            continue
        lines.append(f"### Round {event.get('round', 0)}")
        lines.append("")
        for node in event.get("dag", {}).get("nodes", []):
            lines.append(f"- `{node.get('id')}` → {node.get('task')} (children: {node.get('children', [])})")
        lines.append("")

    lines.extend(["## Retrieved evidence", ""])
    for index, row in enumerate(retrievals):
        lines.extend([f"### Retrieval {index}: {row.get('query', '')}", ""])
        for item in retrieval_details(row):
            evidence = item.get("text_content") or item.get("content")
            lines.extend(
                [
                    f"- Node `{item.get('node_id', 'unknown')}`; type `{item.get('type', 'unknown')}`; visual `{item.get('visual', False)}`",
                    "",
                    clipped(evidence, 3000),
                    "",
                ]
            )

    lines.extend(["## Worker outputs", ""])
    for event in events:
        if event.get("event") != "worker_result":
            continue
        lines.extend(
            [
                f"### Round {event.get('round', 0)}, node `{event.get('node_id')}`",
                "",
                f"Task: {event.get('task')}",
                "",
                clipped(event.get("response")),
                "",
            ]
        )

    lines.extend(["## Sufficiency checks", ""])
    for event in events:
        if event.get("event") == "evidence_check":
            lines.extend(
                [
                    f"### Round {event.get('round', 0)} — parsed={event.get('parsed')}, sufficient={event.get('sufficient')}",
                    "",
                    clipped(event.get("response")),
                    "",
                ]
            )
    endings = [event for event in events if event.get("event") == "question_end"]
    lines.extend(["## Final synthesis", "", clipped(endings[-1].get("response") if endings else "missing"), ""])
    lines.extend(
        [
            "## Causal classification (human/teacher validation required)",
            "",
            "- Primary category: pending",
            "- Necessary evidence retrieved: pending",
            "- Low-resource confound: pending",
            "- Supporting trace event/node IDs: pending",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    summary_path = ROOT / "TRACE_SUMMARY.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    PACKETS.mkdir(parents=True, exist_ok=True)
    index = ["# Failure-review packets", ""]
    for row in summary["questions"]:
        if not row.get("review_flags"):
            continue
        target = PACKETS / f"{row['question_id']}.md"
        target.write_text(make_packet(row), encoding="utf-8")
        index.append(f"- `{row['question_id']}.md`: {', '.join(row['review_flags'])}")
    (PACKETS / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

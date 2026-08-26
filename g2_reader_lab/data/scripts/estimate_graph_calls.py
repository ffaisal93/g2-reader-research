"""Estimate Content Graph node/call counts without loading image payloads or models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from minig2.processed import _content_list


def node_counts(root: Path, dataset: str, document: str, chunk_size: int) -> tuple[int, int]:
    content = _content_list(root, dataset, document)
    raw = json.loads(content.read_text(encoding="utf-8"))
    text_nodes = visual_nodes = 0
    length = 0
    for item in raw:
        if str(item.get("type", "text")) == "text":
            value = str(item.get("text", ""))
            if length and length + len(value) > chunk_size:
                text_nodes += (length + chunk_size - 1) // chunk_size
                length = 0
            length += len(value)
        else:
            if length:
                text_nodes += (length + chunk_size - 1) // chunk_size
                length = 0
            visual_nodes += 1
    if length:
        text_nodes += (length + chunk_size - 1) // chunk_size
    return text_nodes, visual_nodes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--processed-root", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=3000)
    parser.add_argument("--evolution-rounds", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache: dict[tuple[str, str], tuple[int, int]] = {}
    questions = []
    with args.questions.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            missing = []
            text_nodes = visual_nodes = 0
            for document in row["documents"]:
                key = row["dataset"], document
                try:
                    cache.setdefault(key, node_counts(args.processed_root, *key, args.chunk_size))
                except FileNotFoundError:
                    missing.append(document)
                    continue
                text, visual = cache[key]
                text_nodes += text
                visual_nodes += visual
            nodes = text_nodes + visual_nodes
            questions.append(
                {
                    "id": row["id"],
                    "dataset": row["dataset"],
                    "documents": len(row["documents"]),
                    "missing_documents": missing,
                    "text_nodes": text_nodes,
                    "visual_nodes": visual_nodes,
                    "content_nodes": nodes,
                    "minimum_content_graph_vlm_calls": nodes * (1 + args.evolution_rounds),
                    "maximum_with_three_structured_attempts": nodes * (1 + args.evolution_rounds) * 3,
                }
            )
    report = {
        "questions": questions,
        "question_count": len(questions),
        "missing_document_count": sum(len(row["missing_documents"]) for row in questions),
        "content_nodes": sum(row["content_nodes"] for row in questions),
        "minimum_content_graph_vlm_calls": sum(row["minimum_content_graph_vlm_calls"] for row in questions),
        "maximum_with_three_structured_attempts": sum(row["maximum_with_three_structured_attempts"] for row in questions),
        "excludes_online_planning_worker_check_refinement_calls": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "questions"}, indent=2))


if __name__ == "__main__":
    main()

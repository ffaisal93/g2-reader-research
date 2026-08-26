"""Freeze a proportional, reproducible SPIQA sample before inspecting outputs."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


NUMBER = re.compile(r"^\s*[-+]?\d+(?:\.\d+)?(?:\s*%|\s*[a-zA-Z]+)?\s*$")
EXPLICIT_VISUAL = re.compile(r"\b(?:fig(?:ure)?\.?|table|chart|plot|diagram)\s*\d*\b", re.I)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_score(seed: str, question_id: str) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode()).hexdigest()


def classify(record: dict) -> tuple[str, str, str]:
    documents = ast.literal_eval(record["documents"])
    count = len(documents)
    bucket = "1-5" if count <= 5 else "6-10" if count <= 10 else "11+"
    answer_type = "number" if NUMBER.fullmatch(str(record["answer"]).strip()) else "text"
    explicit = "explicit_visual" if EXPLICIT_VISUAL.search(record["question"]) else "implicit_visual"
    return answer_type, explicit, bucket


def allocate(groups: dict[tuple[str, str, str], list[dict]], target: int) -> dict:
    total = sum(map(len, groups.values()))
    raw = {key: target * len(rows) / total for key, rows in groups.items()}
    allocation = {key: min(len(groups[key]), math.floor(value)) for key, value in raw.items()}
    remaining = target - sum(allocation.values())
    order = sorted(groups, key=lambda key: (-(raw[key] - math.floor(raw[key])), key))
    while remaining:
        progressed = False
        for key in order:
            if allocation[key] < len(groups[key]):
                allocation[key] += 1
                remaining -= 1
                progressed = True
                if not remaining:
                    break
        if not progressed:
            raise RuntimeError("unable to allocate requested sample")
    return allocation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--document-manifest", type=Path, required=True)
    parser.add_argument("--target", type=int, default=100)
    parser.add_argument("--seed", default="official-g2-spiqa-audit-v1")
    args = parser.parse_args()

    records = [json.loads(line) for line in args.source.read_text(encoding="utf-8").splitlines() if line]
    if not records or args.target <= 0 or args.target > len(records):
        raise ValueError("target must be between one and the source record count")
    if any(record.get("sub_domain") != "spiqa" for record in records):
        raise ValueError("source must contain only SPIQA records")

    groups = defaultdict(list)
    for record in records:
        groups[classify(record)].append(record)
    allocation = allocate(groups, args.target)

    selected = []
    for key, rows in groups.items():
        ranked = sorted(rows, key=lambda row: (stable_score(args.seed, row["_id"]), row["_id"]))
        selected.extend(ranked[: allocation[key]])
    selected.sort(key=lambda row: (stable_score(args.seed, row["_id"]), row["_id"]))

    documents = sorted(
        {
            document
            for record in selected
            for document in ast.literal_eval(record["documents"])[:5]
        }
    )
    population_counts = Counter("|".join(classify(record)) for record in records)
    sample_counts = Counter("|".join(classify(record)) for record in selected)

    args.questions.parent.mkdir(parents=True, exist_ok=True)
    args.questions.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected), encoding="utf-8")
    args.document_manifest.write_text(
        json.dumps(
            {
                "dataset": "spiqa",
                "scope": "first five documents listed per question, as hard-coded by the official runtime",
                "documents": [{"dataset": "spiqa", "document": document} for document in documents],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    args.manifest.write_text(
        json.dumps(
            {
                "name": "official_g2_spiqa_audit_v1",
                "seed": args.seed,
                "selection": "SHA-256 stable sampling with proportional allocation across answer type, explicit visual reference, and listed-document-count strata",
                "source": str(args.source.resolve()),
                "source_sha256": digest(args.source),
                "population_size": len(records),
                "sample_size": len(selected),
                "official_document_scope": "first five listed documents",
                "unique_required_document_count": len(documents),
                "population_strata": dict(sorted(population_counts.items())),
                "sample_strata": dict(sorted(sample_counts.items())),
                "question_ids": [row["_id"] for row in selected],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

"""Create deterministic, document-complete VisDoMBench development slices."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PyPDF2 import PdfReader

SEED = 20260817
DATASETS = {
    "feta_tab": ("processed_feta_tab.jsonl", "feta_tab", "table"),
    "paper_tab": ("processed_paper_tab.jsonl", "paper_tab", "table"),
    "spiqa": ("processed_spiqa.jsonl", "spiqa", "figure"),
    "scigraphqa": ("processed_scigraphvqa.jsonl", "scigraphvqa", "figure"),
    "slidevqa": ("processed_slidevqa.jsonl", "slidevqa", "slide"),
}


@dataclass(frozen=True)
class Exclusion:
    sample_id: str
    reason: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def parse_documents(value: Any) -> list[str]:
    if isinstance(value, list):
        documents = value
    elif isinstance(value, str):
        try:
            documents = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"invalid documents literal: {value!r}") from exc
    else:
        raise ValueError(f"unsupported documents value: {type(value).__name__}")
    if not isinstance(documents, list) or not all(isinstance(item, str) for item in documents):
        raise ValueError("documents must resolve to a list of strings")
    return documents


def normalize_answer(row: dict[str, Any]) -> Any:
    raw = row.get("answer")
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            return ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            pass
    return stripped


def answer_type(answer: Any) -> str:
    if isinstance(answer, (list, tuple, set)):
        return "list"
    if isinstance(answer, dict):
        return "list" if len(answer) > 1 else "text"
    text = str(answer).strip()
    numeric = re.fullmatch(r"[-+]?[$£€]?\d[\d,]*(?:\.\d+)?(?:\s*(?:%|bn|million|billion|years?|km|kg))?", text, re.I)
    if numeric:
        return "number"
    if "\n-" in text or (text.count(";") >= 2 and len(text) < 500):
        return "list"
    return "text"


def evidence_type(question: str, default: str) -> str:
    lowered = question.lower()
    if "table" in lowered:
        return "table"
    if "chart" in lowered or "graph" in lowered or re.search(r"\bfig(?:ure)?\.?\s*\d", lowered):
        return "chart/figure"
    if "slide" in lowered:
        return "slide"
    return default


def hop_type(question: str) -> str:
    lowered = question.lower()
    compositional_markers = (
        "difference between",
        "ratio of",
        "compared with",
        "in the year",
        "respectively",
        "both ",
        " and why",
    )
    return "compositional" if any(marker in lowered for marker in compositional_markers) else "unknown"


def stable_rank(sample_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{sample_id}".encode()).hexdigest()


def validate_pdf(path: Path) -> str | None:
    if not path.is_file():
        return "document missing"
    try:
        reader = PdfReader(path, strict=False)
        if not reader.pages:
            return "PDF has no pages"
        _ = reader.pages[0].mediabox
    except Exception as exc:  # capture exact third-party parser failure for report
        return f"PDF parse failed: {type(exc).__name__}: {exc}"
    return None


def enrich_row(row: dict[str, Any], dataset: str, default_evidence: str) -> dict[str, Any]:
    documents = parse_documents(row.get("documents"))
    answer = normalize_answer(row)
    return {
        "id": row["_id"],
        "original_id": row["_id"],
        "dataset": dataset,
        "domain": row.get("domain"),
        "sub_domain": row.get("sub_domain"),
        "question": row["question"],
        "answer": answer,
        "answer_raw": row.get("answer"),
        "documents": documents,
        "main_document": row.get("main_doc"),
        "evidence_annotations": row.get("evidence"),
        "sampling_attributes": {
            "answer_type": answer_type(answer),
            "evidence_type": evidence_type(row["question"], default_evidence),
            "hop_type": hop_type(row["question"]),
            "document_count": len(documents),
            "explicit_figure_or_table_reference": bool(
                re.search(r"\b(?:fig(?:ure)?|table|chart)\b", row["question"], re.I)
            ),
        },
    }


def interleave_by_answer_type(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row["sampling_attributes"]["answer_type"]].append(row)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: stable_rank(item["id"]))

    ordered = []
    preferred = ("number", "list", "text")
    while any(buckets.values()):
        for kind in preferred:
            if buckets[kind]:
                ordered.append(buckets[kind].pop(0))
        for kind in sorted(set(buckets) - set(preferred)):
            if buckets[kind]:
                ordered.append(buckets[kind].pop(0))
    return ordered


def select_dataset(
    rows: list[dict[str, Any]],
    dataset: str,
    document_dir: Path,
    count: int,
    default_evidence: str,
) -> tuple[list[dict[str, Any]], list[Exclusion]]:
    candidates = interleave_by_answer_type(enrich_row(row, dataset, default_evidence) for row in rows)
    selected: list[dict[str, Any]] = []
    exclusions: list[Exclusion] = []
    seen_ids: set[str] = set()
    validation_cache: dict[Path, str | None] = {}
    for row in candidates:
        if row["id"] in seen_ids:
            exclusions.append(Exclusion(row["id"], "duplicate stable ID in released metadata"))
            continue
        seen_ids.add(row["id"])
        failures = []
        if row["main_document"] not in row["documents"]:
            failures.append("main document is absent from documents list")
        for document in row["documents"]:
            path = document_dir / document
            if path not in validation_cache:
                validation_cache[path] = validate_pdf(path)
            if validation_cache[path]:
                failures.append(f"{document}: {validation_cache[path]}")
        if failures:
            exclusions.append(Exclusion(row["id"], "; ".join(failures)))
            continue
        row["document_paths"] = [str((document_dir / name).resolve()) for name in row["documents"]]
        selected.append(row)
        if len(selected) == count:
            break
    return selected, exclusions


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def distribution(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(row["sampling_attributes"][field] for row in rows).items()))


def freeze_slice(output_dir: Path, rows: list[dict[str, Any]], exclusions: list[Exclusion]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "questions.jsonl", rows)
    config_hash = hashlib.sha256(
        json.dumps({"seed": SEED, "ids": [row["id"] for row in rows]}, sort_keys=True).encode()
    ).hexdigest()
    manifest = {
        "seed": SEED,
        "selection_algorithm": "SHA-256(seed:id), interleaved by inferred answer type",
        "configuration_hash": config_hash,
        "question_count": len(rows),
        "ids": [row["id"] for row in rows],
        "dataset_counts": dict(sorted(Counter(row["dataset"] for row in rows).items())),
        "answer_type_counts": distribution(rows, "answer_type"),
        "evidence_type_counts": distribution(rows, "evidence_type"),
        "hop_type_counts": distribution(rows, "hop_type"),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    unique_documents: dict[str, dict[str, Any]] = {}
    for row in rows:
        for name, path_string in zip(row["documents"], row["document_paths"], strict=True):
            path = Path(path_string)
            key = f"{row['dataset']}:{name}"
            unique_documents[key] = {
                "dataset": row["dataset"],
                "document": name,
                "path": path_string,
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "validated_with": "PyPDF2 first-page mediabox",
            }
    document_manifest = {
        "document_count": len(unique_documents),
        "documents": [unique_documents[key] for key in sorted(unique_documents)],
    }
    (output_dir / "document_manifest.json").write_text(
        json.dumps(document_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    exclusion_lines = "\n".join(f"- `{item.sample_id}`: {item.reason}" for item in exclusions)
    if not exclusion_lines:
        exclusion_lines = "- None encountered before each dataset quota was filled."
    report = f"""# Selection Report

## Method

- Fixed seed: `{SEED}`.
- Rows are ranked by `SHA-256(seed:id)` and interleaved by inferred answer type.
- Selection never uses baseline output or model correctness.
- Every listed PDF must exist, contain at least one page, and expose a readable first-page media box.
- Smoke is a deterministic subset of mini: the first three selected rows per dataset.
- Evidence type defaults to the dataset modality and is refined only by explicit words in the question.
- Hop labels remain `unknown` unless a documented lexical compositional marker is present; released metadata has no hop annotation.

## Distribution

```json
{json.dumps(manifest, indent=2)}
```

## Recorded exclusions encountered before quotas were filled

{exclusion_lines}
"""
    (output_dir / "selection_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--visdom-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    mini_rows: list[dict[str, Any]] = []
    smoke_rows: list[dict[str, Any]] = []
    all_exclusions: list[Exclusion] = []
    for dataset, (metadata_name, visdom_name, default_evidence) in DATASETS.items():
        rows = load_jsonl(args.metadata_dir / metadata_name)
        selected, exclusions = select_dataset(
            rows,
            dataset,
            args.visdom_dir / visdom_name / "docs",
            20,
            default_evidence,
        )
        mini_rows.extend(selected)
        smoke_rows.extend(selected[:3])
        all_exclusions.extend(exclusions)

    freeze_slice(args.output_root / "mini", mini_rows, all_exclusions)
    freeze_slice(args.output_root / "smoke", smoke_rows, all_exclusions)


if __name__ == "__main__":
    main()

"""Materialize released-schema JSONL rows in a frozen slice's exact order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


METADATA = {
    "feta_tab": "processed_feta_tab.jsonl",
    "paper_tab": "processed_paper_tab.jsonl",
    "spiqa": "processed_spiqa.jsonl",
    "scigraphqa": "processed_scigraphvqa.jsonl",
    "slidevqa": "processed_slidevqa.jsonl",
}


def rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        yield from (json.loads(line) for line in handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = list(rows(args.slice))
    indexes = {
        dataset: {row["_id"]: row for row in rows(args.metadata_dir / filename)}
        for dataset, filename in METADATA.items()
    }
    released = [indexes[item["dataset"]][item["id"]] for item in selected]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for item in released:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "rows": len(released)}))


if __name__ == "__main__":
    main()

"""Select the first frozen smoke example from each dataset without resampling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected: dict[str, dict] = {}
    with args.input.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            selected.setdefault(row["dataset"], row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        for row in selected.values():
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"rows": len(selected), "ids": [row["id"] for row in selected.values()]}))


if __name__ == "__main__":
    main()

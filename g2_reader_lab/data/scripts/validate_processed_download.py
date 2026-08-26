"""Validate a selective processed-data snapshot without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from estimate_hf_payload import REPO_ID, REVISION, document_prefix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-manifest", type=Path, required=True)
    parser.add_argument("--estimate", type=Path, required=True)
    parser.add_argument("--processed-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.document_manifest.read_text(encoding="utf-8"))
    estimate = json.loads(args.estimate.read_text(encoding="utf-8"))
    estimate_by_prefix = {item["prefix"]: item for item in estimate["documents"]}
    checks = []
    for item in manifest["documents"]:
        prefix = document_prefix(item["dataset"], item["document"])
        directory = args.processed_root / prefix
        files = [path for path in directory.rglob("*") if path.is_file()]
        expected = estimate_by_prefix[prefix]
        content_lists = [path for path in files if path.name.endswith("_content_list.json")]
        checks.append(
            {
                "dataset": item["dataset"],
                "document": item["document"],
                "prefix": prefix,
                "exists": directory.is_dir(),
                "content_list_count": len(content_lists),
                "file_count": len(files),
                "expected_file_count": expected["file_count"],
                "bytes": sum(path.stat().st_size for path in files),
                "expected_bytes": expected["size_bytes"],
            }
        )

    failed = [
        item
        for item in checks
        if not item["exists"]
        or item["content_list_count"] < 1
        or item["file_count"] != item["expected_file_count"]
        or item["bytes"] != item["expected_bytes"]
    ]
    report = {
        "repo_id": REPO_ID,
        "revision": REVISION,
        "document_count": len(checks),
        "valid_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "actual_bytes": sum(item["bytes"] for item in checks),
        "expected_bytes": sum(item["expected_bytes"] for item in checks),
        "documents": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "documents"}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

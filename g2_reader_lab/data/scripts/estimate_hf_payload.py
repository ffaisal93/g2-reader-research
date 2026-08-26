"""Estimate selected processed-document bytes from Hugging Face metadata only."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi
from huggingface_hub.hf_api import RepoFile

REPO_ID = "LittleWhite1031/G2-Reader"
REVISION = "57d76a6ab4872592dfe47dbf4fae6cd77bcf184b"
HF_DIRS = {
    "feta_tab": "fetatab",
    "paper_tab": "papertab",
    "spiqa": "spiqa",
    "scigraphqa": "scgqa/mineru_result",
    "slidevqa": "slide",
}


def document_prefix(dataset: str, document: str) -> str:
    stem = document[:-4] if document.lower().endswith(".pdf") else document
    return f"{HF_DIRS[dataset]}/{stem}"


def inspect_prefix(api: HfApi, dataset: str, document: str) -> dict[str, Any]:
    prefix = document_prefix(dataset, document)
    entries = list(
        api.list_repo_tree(
            REPO_ID,
            path_in_repo=prefix,
            recursive=True,
            expand=True,
            revision=REVISION,
            repo_type="dataset",
        )
    )
    files = [entry for entry in entries if isinstance(entry, RepoFile)]
    total = sum((entry.lfs or {}).get("size", entry.size or 0) for entry in files)
    return {
        "dataset": dataset,
        "document": document,
        "prefix": prefix,
        "file_count": len(files),
        "size_bytes": total,
        "found": bool(files),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    source = json.loads(args.document_manifest.read_text(encoding="utf-8"))
    api = HfApi()
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(inspect_prefix, api, item["dataset"], item["document"]): item
            for item in source["documents"]
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append(
                    {
                        "dataset": item["dataset"],
                        "document": item["document"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    results.sort(key=lambda item: (item["dataset"], item["document"]))
    payload = {
        "repo_id": REPO_ID,
        "revision": REVISION,
        "document_count": len(results),
        "found_count": sum(item["found"] for item in results),
        "estimated_bytes": sum(item["size_bytes"] for item in results),
        "errors": errors,
        "documents": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in payload if key != "documents"}, indent=2))


if __name__ == "__main__":
    main()

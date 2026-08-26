"""Download only processed document directories selected by a slice manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import snapshot_download

from estimate_hf_payload import REPO_ID, REVISION, document_prefix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.document_manifest.read_text(encoding="utf-8"))
    prefixes = sorted(
        {
            document_prefix(item["dataset"], item["document"])
            for item in manifest["documents"]
        }
    )
    patterns = [f"{prefix}/**" for prefix in prefixes]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        revision=REVISION,
        allow_patterns=patterns,
        local_dir=args.output_dir,
        max_workers=1,
    )
    print(
        json.dumps(
            {
                "repo_id": REPO_ID,
                "revision": REVISION,
                "document_count": len(prefixes),
                "output_dir": str(Path(path).resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

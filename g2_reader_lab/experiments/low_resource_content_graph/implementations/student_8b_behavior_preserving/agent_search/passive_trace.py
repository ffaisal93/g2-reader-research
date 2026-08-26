"""Best-effort JSONL event capture for the frozen official runtime.

Tracing must never change a model input, output, retry, graph, or decision. All
I/O errors are therefore swallowed and reported only to stderr.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any


def append_event(save_dir: str, question_id: str, event: str, payload: dict[str, Any]) -> None:
    try:
        trace_dir = Path(save_dir) / "logs" / f"data_{question_id}"
        trace_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.time(),
            "question_id": str(question_id),
            "event": event,
            **payload,
        }
        with (trace_dir / "official_trace.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # tracing is observational and must never stop G2
        print(f"Passive trace write failed: {exc}", file=sys.stderr)


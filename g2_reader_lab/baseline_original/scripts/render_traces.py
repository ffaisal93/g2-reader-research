"""Render corrected-upstream JSONL/log artifacts into compact per-question traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in jsonl(args.input):
        question_id = str(item["_id"])
        runtime_trace = item.get("trace", {})
        retrieval_path = Path(runtime_trace.get("retrieval_log", ""))
        trace = {
            "question_id": question_id,
            "question": item.get("question"),
            "answer": item.get("answer"),
            "prediction": item.get("pred"),
            "process_time": item.get("process_time"),
            "usage": item.get("usage"),
            "content_graph": runtime_trace.get("content_graph"),
            "initial_retrieval_and_worker_retrievals": jsonl(retrieval_path),
            "initial_planning_graph": runtime_trace.get("initial_planning_graph"),
            "planning_graphs": runtime_trace.get("planning_graphs", []),
            "execution_orders": runtime_trace.get("execution_orders", []),
            "evidence_checks": runtime_trace.get("evidence_checks", []),
            "node_trajectory": runtime_trace.get("node_trajectory", []),
            "final_response": runtime_trace.get("final_response"),
        }
        machine = args.output_dir / f"{question_id}.json"
        human = args.output_dir / f"{question_id}.md"
        machine.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        calls = (trace.get("usage") or {}).get("calls", [])
        retrievals = trace["initial_retrieval_and_worker_retrievals"]
        lines = [
            f"# Corrected baseline trace: {question_id}",
            "",
            f"Question: {trace['question']}",
            "",
            f"Content Graph: `{trace['content_graph']}`",
            f"Retrieval events: {len(retrievals)}",
            f"Initial Planning Graph: `{trace['initial_planning_graph']}`",
            f"Execution orders: `{trace['execution_orders']}`",
            f"Evidence checks: `{trace['evidence_checks']}`",
            f"Intermediate answers: `{trace['node_trajectory']}`",
            "",
            "## Runtime",
            "",
            f"Model calls: {len(calls)}",
            f"Total tokens: {(trace.get('usage') or {}).get('total_tokens')}",
            f"Peak VRAM: {(trace.get('usage') or {}).get('peak_vram_bytes')} bytes",
            f"Wall time: {trace['process_time']} seconds",
            "",
            "## Final",
            "",
            f"Prediction: {trace['prediction']}",
            f"Reference: {trace['answer']}",
            "",
        ]
        human.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"traces": len(jsonl(args.input)), "output_dir": str(args.output_dir)}))


if __name__ == "__main__":
    main()

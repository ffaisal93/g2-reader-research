#!/usr/bin/env python3
"""Consolidate the fixed five-question loss evaluation into one JSON artifact."""

from __future__ import annotations

import json
from pathlib import Path


LAB = Path("/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab")
ROOT = LAB / "experiments/low_resource_content_graph/loss_evaluation"
QUESTIONS = ["spiqa_58", "spiqa_108", "spiqa_378", "spiqa_540", "spiqa_542"]

CANDIDATE_BUILD = {
    "spiqa_58": LAB / "experiments/low_resource_content_graph/results/final_v1/spiqa_58/result.json",
    "spiqa_108": LAB / "experiments/low_resource_content_graph/results/final_v1/spiqa_108/result.json",
    "spiqa_378": LAB / "experiments/low_resource_content_graph/results/expansion_v3/spiqa_378/result.json",
    "spiqa_540": ROOT / "candidate_builds/spiqa_540/result.json",
    "spiqa_542": ROOT / "candidate_builds/spiqa_542/result.json",
}

# These are the best recoverable official-style construction measurements for
# the exact saved teacher graph set. Four are sums of the instrumented official
# construction-stage wall times. spiqa_378 is elapsed time from construction
# start (23:16:15) to the first post-build retrieval event (23:55:22), because
# its online run lost the server before usage_time.jsonl could be written.
TEACHER_BUILD = {
    "spiqa_58": {"seconds": 3227.841338634491, "measurement": "instrumented stage-duration sum"},
    "spiqa_108": {"seconds": 2392.512250185013, "measurement": "instrumented stage-duration sum"},
    "spiqa_378": {"seconds": 2347.0, "measurement": "console timestamp estimate", "approximate": True},
    "spiqa_540": {"seconds": 4225.99508190155, "measurement": "instrumented stage-duration sum"},
    "spiqa_542": {"seconds": 2706.366603374481, "measurement": "instrumented stage-duration sum"},
}

ASSESSMENT = {
    "spiqa_58": {
        "teacher_correct": True,
        "candidate_parsed_correct": True,
        "candidate_raw_correct": True,
        "decisive_evidence_in_candidate_top5": True,
        "primary_observation": "No material loss; paired answers are substantively equivalent.",
        "failure_category": None,
    },
    "spiqa_108": {
        "teacher_correct": True,
        "candidate_parsed_correct": False,
        "candidate_raw_correct": True,
        "decisive_evidence_in_candidate_top5": True,
        "primary_observation": "Correct raw conclusion, but four refinement rounds and missing closing output tag produced a null parsed prediction.",
        "failure_category": "sufficiency_and_parser_failure",
    },
    "spiqa_378": {
        "teacher_correct": True,
        "candidate_parsed_correct": True,
        "candidate_raw_correct": True,
        "decisive_evidence_in_candidate_top5": True,
        "primary_observation": "Candidate Worker initially misread the NoCorrect row; global refinement recovered the exact answer at 3.86x teacher latency.",
        "failure_category": "worker_support_failure_repaired_by_refinement",
    },
    "spiqa_540": {
        "teacher_correct": True,
        "candidate_parsed_correct": False,
        "candidate_raw_correct": False,
        "decisive_evidence_in_candidate_top5": True,
        "primary_observation": "Confirmed accuracy loss: correct Figure 3 ranked first and OCR said Left L=9, but the Worker misread the panels and answered that information was unavailable.",
        "failure_category": "worker_support_failure_from_weaker_visual_summary",
    },
    "spiqa_542": {
        "teacher_correct": True,
        "candidate_parsed_correct": True,
        "candidate_raw_correct": True,
        "decisive_evidence_in_candidate_top5": True,
        "primary_observation": "Correct answer, but unnecessary refinement raised query latency from 21.08 to 86.02 seconds.",
        "failure_category": "sufficiency_inefficiency",
    },
}


def read_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text.splitlines()[0])


def candidate_usage(record: dict) -> dict:
    calls = record["usage"]["calls"]
    chats = [call for call in calls if call["type"] == "chat"]
    embeds = [call for call in calls if call["type"] == "embed"]
    return {
        "chat_calls": len(chats),
        "vlm_tokens": sum(call.get("total_tokens", 0) for call in chats),
        "embedding_calls": len(embeds),
        "embedding_tokens": record["usage"].get("embedding_tokens", 0),
    }


def main() -> None:
    rows = []
    for question_id in QUESTIONS:
        candidate_build = read_json(CANDIDATE_BUILD[question_id])
        retrieval = read_json(ROOT / f"retrieval/{question_id}.json")
        teacher_qa_path = ROOT / f"matched_qa/teacher_graph/{question_id}/local-qwen-vl_dag_rag_1.jsonl"
        candidate_qa_path = ROOT / f"matched_qa/candidate_graph/{question_id}/local-qwen-vl_dag_rag_1.jsonl"
        teacher_qa = read_json(teacher_qa_path)
        candidate_qa = read_json(candidate_qa_path)
        candidate_graph = retrieval["graphs"]["candidate"]
        teacher_graph = retrieval["graphs"]["teacher_32b"]

        row = {
            "question_id": question_id,
            "question": retrieval["question"],
            "reference_answer": retrieval["reference_answer"],
            "construction": {
                "teacher_32b": TEACHER_BUILD[question_id],
                "candidate_8b": {
                    "seconds": candidate_build["duration_total_sec"],
                    "nodes": candidate_build["node_count"],
                    **candidate_usage(candidate_build),
                },
                "speedup": TEACHER_BUILD[question_id]["seconds"] / candidate_build["duration_total_sec"],
            },
            "retrieval": {
                "k": retrieval["k"],
                "teacher_nodes": teacher_graph["node_count"],
                "candidate_nodes": candidate_graph["node_count"],
                "raw_overlap_at_5": candidate_graph["overlap_with_teacher_32b_at_5"],
                "teacher_traced_text_hits": candidate_graph["teacher_text_evidence_hits"],
                "teacher_traced_text_total": candidate_graph["teacher_text_evidence_total"],
                "decisive_evidence_in_candidate_top5": ASSESSMENT[question_id]["decisive_evidence_in_candidate_top5"],
            },
            "matched_online_reader": {
                "model": "Qwen3-VL-8B-Instruct-FP8",
                "seed": 42,
                "teacher_graph": {
                    "prediction": teacher_qa.get("pred"),
                    "seconds": teacher_qa["process_time"],
                    "correct": ASSESSMENT[question_id]["teacher_correct"],
                    "artifact": str(teacher_qa_path),
                },
                "candidate_graph": {
                    "prediction": candidate_qa.get("pred"),
                    "raw_response": candidate_qa.get("response"),
                    "seconds": candidate_qa["process_time"],
                    "parsed_correct": ASSESSMENT[question_id]["candidate_parsed_correct"],
                    "raw_semantically_correct": ASSESSMENT[question_id]["candidate_raw_correct"],
                    "artifact": str(candidate_qa_path),
                },
            },
            "assessment": {
                "primary_observation": ASSESSMENT[question_id]["primary_observation"],
                "failure_category": ASSESSMENT[question_id]["failure_category"],
            },
        }
        rows.append(row)

    teacher_query_seconds = [row["matched_online_reader"]["teacher_graph"]["seconds"] for row in rows]
    candidate_query_seconds = [row["matched_online_reader"]["candidate_graph"]["seconds"] for row in rows]
    teacher_build_seconds = [row["construction"]["teacher_32b"]["seconds"] for row in rows]
    candidate_build_seconds = [row["construction"]["candidate_8b"]["seconds"] for row in rows]
    report = {
        "protocol": str(ROOT / "EVALUATION_PROTOCOL.md"),
        "sample_size": len(rows),
        "questions": rows,
        "summary": {
            "teacher_graph_matched_reader_correct": sum(row["matched_online_reader"]["teacher_graph"]["correct"] for row in rows),
            "candidate_graph_parsed_correct": sum(row["matched_online_reader"]["candidate_graph"]["parsed_correct"] for row in rows),
            "candidate_graph_raw_semantically_correct": sum(row["matched_online_reader"]["candidate_graph"]["raw_semantically_correct"] for row in rows),
            "candidate_decisive_evidence_present_at_5": sum(row["retrieval"]["decisive_evidence_in_candidate_top5"] for row in rows),
            "raw_top5_overlap_total": sum(row["retrieval"]["raw_overlap_at_5"] for row in rows),
            "raw_top5_overlap_possible": 5 * len(rows),
            "raw_top5_overlap_rate": sum(row["retrieval"]["raw_overlap_at_5"] for row in rows) / (5 * len(rows)),
            "mean_teacher_build_seconds": sum(teacher_build_seconds) / len(rows),
            "mean_candidate_build_seconds": sum(candidate_build_seconds) / len(rows),
            "mean_construction_speedup": (sum(teacher_build_seconds) / len(rows)) / (sum(candidate_build_seconds) / len(rows)),
            "max_candidate_build_seconds": max(candidate_build_seconds),
            "mean_teacher_graph_query_seconds": sum(teacher_query_seconds) / len(rows),
            "mean_candidate_graph_query_seconds": sum(candidate_query_seconds) / len(rows),
            "candidate_query_slowdown": (sum(candidate_query_seconds) / len(rows)) / (sum(teacher_query_seconds) / len(rows)),
        },
        "claim_limit": "Fixed five-question pilot; too small for a dataset-level no-regression or production claim.",
    }
    (ROOT / "RESULTS.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

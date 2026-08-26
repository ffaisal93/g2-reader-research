#!/usr/bin/env python3
"""Compare fixed-question retrieval across teacher and student G2 graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--teacher-retrieval-jsonl", type=Path, required=True)
    parser.add_argument("--teacher-graph", type=Path, required=True)
    parser.add_argument("--baseline-graph", type=Path)
    parser.add_argument("--candidate-graph", type=Path, required=True)
    parser.add_argument("--embedding-base-url", default="http://127.0.0.1:18001/v1")
    parser.add_argument("--embedding-model", default="local-bge-m3")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("-k", type=int, default=5)
    return parser.parse_args()


def content_hash(note) -> str:
    return hashlib.sha256(note.content.encode("utf-8")).hexdigest()


def load_graph(path: Path):
    with (path / "memories.pkl").open("rb") as handle:
        memories = list(pickle.load(handle).values())
    embeddings = np.load(path / "retriever_embeddings.npy")
    if len(memories) != len(embeddings):
        raise RuntimeError(f"node/vector mismatch in {path}")
    return memories, embeddings


def retrieve(memories, embeddings, query_vector, k: int):
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vector)
    scores = embeddings @ query_vector / np.maximum(norms, 1e-12)
    semantic = np.argsort(scores)[-30:][::-1]
    selected: list[int] = []
    for raw_index in semantic:
        index = int(raw_index)
        if index not in selected:
            selected.append(index)
        if len(selected) >= k:
            break
        for neighbor in memories[index].links[:3]:
            neighbor = int(neighbor)
            if 0 <= neighbor < len(memories) and neighbor not in selected:
                selected.append(neighbor)
            if len(selected) >= k:
                break
        if len(selected) >= k:
            break
    return [
        {
            "index": index,
            "content_hash": content_hash(memories[index]),
            "visual": bool(memories[index].visual),
            "score": float(scores[index]),
            "summary": memories[index].context,
            "preview": (
                memories[index].text_content
                if memories[index].visual
                else memories[index].content
            )[:500],
        }
        for index in selected
    ]


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(args.source_root.resolve()))
    __import__("prebuild.memory_layer")

    question_record = json.loads(args.input_jsonl.read_text(encoding="utf-8").splitlines()[0])
    query = question_record["question"]
    client = OpenAI(base_url=args.embedding_base_url, api_key="local", timeout=300)
    query_vector = np.asarray(
        client.embeddings.create(model=args.embedding_model, input=query).data[0].embedding
    )

    graphs = {}
    graph_paths = [
        ("teacher_32b", args.teacher_graph),
        ("candidate", args.candidate_graph),
    ]
    if args.baseline_graph is not None:
        graph_paths.insert(1, ("baseline_8b", args.baseline_graph))
    for name, path in graph_paths:
        memories, embeddings = load_graph(path)
        results = retrieve(memories, embeddings, query_vector, args.k)
        graphs[name] = {"node_count": len(memories), "results": results}

    first_trace = json.loads(
        args.teacher_retrieval_jsonl.read_text(encoding="utf-8").splitlines()[0]
    )
    teacher_trace_hashes = []
    for item in first_trace["semantic_retrieval"]["results"][: args.k]:
        content = item.get("content", "")
        if item.get("visual") and content == "[IMAGE_BASE64]":
            # The trace redacts image bytes, so use its text node hashes only.
            continue
        teacher_trace_hashes.append(hashlib.sha256(content.encode("utf-8")).hexdigest())

    for name, graph in graphs.items():
        hashes = {item["content_hash"] for item in graph["results"]}
        graph["teacher_text_evidence_hits"] = sum(h in hashes for h in teacher_trace_hashes)
        graph["teacher_text_evidence_total"] = len(teacher_trace_hashes)

    candidate_hashes = {x["content_hash"] for x in graphs["candidate"]["results"]}
    for comparison in [name for name in ("teacher_32b", "baseline_8b") if name in graphs]:
        other = {x["content_hash"] for x in graphs[comparison]["results"]}
        graphs["candidate"][f"overlap_with_{comparison}_at_{args.k}"] = len(
            candidate_hashes & other
        )

    report = {
        "question_id": question_record["_id"],
        "question": query,
        "reference_answer": question_record["answer"],
        "k": args.k,
        "graphs": graphs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

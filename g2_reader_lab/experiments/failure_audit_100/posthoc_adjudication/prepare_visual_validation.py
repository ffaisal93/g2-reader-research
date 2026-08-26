#!/usr/bin/env python3
"""Prepare provenance-preserving visual review packets for disputed cases.

This script never changes frozen graph/query artifacts. It decodes the exact
base64 image bytes stored in the Content Graph, maps them back to source image
files by SHA-256 when possible, and creates labeled contact sheets for review.
"""

from __future__ import annotations

import base64
import ast
import hashlib
import json
import pickle
import re
import sys
import textwrap
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


LAB = Path("/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab")
AUDIT = LAB / "experiments/failure_audit_100"
ROOT = AUDIT / "posthoc_adjudication"
OUTPUT = ROOT / "visual_validation"
IMPLEMENTATION = LAB / "experiments/low_resource_content_graph/implementations/student_8b_behavior_preserving"
sys.path.insert(0, str(IMPLEMENTATION))

CASES = [
    "spiqa_116", "spiqa_163", "spiqa_164", "spiqa_195",
    "spiqa_215", "spiqa_234", "spiqa_235", "spiqa_281",
    "spiqa_368", "spiqa_452", "spiqa_578", "spiqa_98",
]
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_suffix(data: bytes) -> str:
    with Image.open(BytesIO(data)) as image:
        fmt = (image.format or "PNG").lower()
    return ".jpg" if fmt in {"jpeg", "jpg"} else f".{fmt}"


def difference_hash(image: Image.Image, size: int = 32) -> int:
    gray = image.convert("L").resize((size + 1, size))
    pixels = list(gray.getdata())
    bits = 0
    for row in range(size):
        offset = row * (size + 1)
        for column in range(size):
            bits = (bits << 1) | (pixels[offset + column] > pixels[offset + column + 1])
    return bits


def source_images(documents: list[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for document in documents:
        stem = Path(document).stem
        image_dir = LAB / "data/processed_hf/spiqa" / stem / stem / "auto/images"
        if not image_dir.exists():
            continue
        for path in image_dir.iterdir():
            if not path.is_file():
                continue
            data = path.read_bytes()
            try:
                with Image.open(BytesIO(data)) as image:
                    width, height = image.size
                    image_hash = difference_hash(image)
            except Exception:
                continue
            matches.append({
                "path": str(path), "sha256": sha256(data),
                "width": width, "height": height, "difference_hash": image_hash,
            })
    return matches


def match_sources(data: bytes, candidates: list[dict[str, Any]]) -> tuple[list[str], str, int | None]:
    digest = sha256(data)
    exact = [row["path"] for row in candidates if row["sha256"] == digest]
    if exact:
        return exact, "exact_sha256", 0
    with Image.open(BytesIO(data)) as image:
        width, height = image.size
        image_hash = difference_hash(image)
    same_dimensions = [row for row in candidates if row["width"] == width and row["height"] == height]
    pool = same_dimensions or [
        row for row in candidates
        if abs((row["width"] / row["height"]) - (width / height)) < 0.01
    ]
    if not pool:
        return [], "unmapped", None
    scored = [(int((image_hash ^ row["difference_hash"]).bit_count()), row) for row in pool]
    best_distance = min(score for score, _ in scored)
    best = [row["path"] for score, row in scored if score == best_distance]
    # A 32x32 dHash has 1024 bits. A <=5% distance is conservative for a
    # JPEG-reencoded version of the same extracted figure.
    if best_distance <= 51:
        method = "same_dimensions_perceptual" if same_dimensions else "aspect_ratio_perceptual"
        return best, method, best_distance
    return [], "unmapped", best_distance


def retrieved_visuals(question_id: str) -> dict[str, dict[str, Any]]:
    path = AUDIT / "questions" / question_id / "qa/logs" / f"data_{question_id}" / "retrieval_results.jsonl"
    found: dict[str, dict[str, Any]] = {}
    for event_index, event in enumerate(read_jsonl(path)):
        containers: list[tuple[str, list[dict[str, Any]]]] = []
        semantic = event.get("semantic_retrieval", {}).get("results", [])
        bm25 = event.get("bm25_retrieval", {})
        if semantic:
            containers.append(("initial_semantic", semantic))
        for name in ("text_results", "image_results", "results"):
            value = bm25.get(name, []) if isinstance(bm25, dict) else []
            if isinstance(value, list):
                containers.append((f"initial_bm25_{name}", value))
        details = event.get("results", {}).get("details", [])
        if details:
            containers.append((str(event.get("retrieval_method") or "task_retrieval"), details))
        for method, rows in containers:
            for rank, row in enumerate(rows):
                if row.get("type") != "image" and not row.get("visual"):
                    continue
                node_id = row.get("node_id")
                if not node_id:
                    continue
                record = found.setdefault(node_id, {
                    "node_id": node_id,
                    "text_content": row.get("text_content"),
                    "retrieval_occurrences": [],
                })
                record["retrieval_occurrences"].append({
                    "event_index": event_index,
                    "query": event.get("query"),
                    "method": method,
                    "rank": rank,
                })
    return found


def load_graph(question_id: str) -> dict[str, Any]:
    candidates = [
        AUDIT / "graphs" / f"{question_id}_iter_1" / "memories.pkl",
        AUDIT / "graphs" / f"{question_id}_iter_0" / "memories.pkl",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        raise FileNotFoundError(f"No graph found for {question_id}")
    with path.open("rb") as handle:
        return pickle.load(handle)


def make_contact_sheet(rows: list[dict[str, Any]], target: Path) -> None:
    if not rows:
        return
    font = ImageFont.load_default()
    tile_width, image_height, label_height = 900, 520, 115
    sheet = Image.new("RGB", (tile_width, len(rows) * (image_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        y = index * (image_height + label_height)
        with Image.open(row["decoded_path"]) as source:
            image = source.convert("RGB")
            image.thumbnail((tile_width - 20, image_height - 20))
            x = (tile_width - image.width) // 2
            sheet.paste(image, (x, y + 10))
        cited = "CITED" if row["cited_by_classifier"] else "retrieved"
        source_name = Path(row["source_paths"][0]).name if row["source_paths"] else "unmapped"
        label = f"{index + 1}. {row['node_id']} | {cited} | {row['width']}x{row['height']} | source={source_name}"
        wrapped = textwrap.wrap(label, width=125)
        for line_index, line in enumerate(wrapped[:4]):
            draw.text((8, y + image_height + 5 + line_index * 18), line, fill="black", font=font)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=92)


def main() -> None:
    causal_data = json.loads((ROOT / "CAUSAL_SUMMARY.json").read_text(encoding="utf-8"))
    causal = {row["question_id"]: row["classification"] for row in causal_data["results"]}
    outcomes = {row["question_id"]: row for row in read_jsonl(ROOT / "OUTCOMES.jsonl")}
    replay_path = ROOT / "REPLAY_ADJUDICATION.json"
    replay = {}
    if replay_path.exists():
        replay = {row["question_id"]: row for row in json.loads(replay_path.read_text(encoding="utf-8"))["results"]}

    inventory = []
    for question_id in CASES:
        question_row = json.loads((AUDIT / "questions" / question_id / "input.jsonl").read_text(encoding="utf-8").splitlines()[0])
        documents = [str(value) for value in ast.literal_eval(question_row["documents"])]
        sources = source_images(documents)
        graph = load_graph(question_id)
        notes = {getattr(note, "id", key): note for key, note in graph.items()}
        retrieved = retrieved_visuals(question_id)
        classification = causal[question_id]
        cited_ids = set(classification.get("decisive_evidence_node_ids", [])) | set(UUID_RE.findall(classification.get("rationale", "")))
        selected_ids = set(retrieved) | cited_ids
        case_dir = OUTPUT / "cases" / question_id
        node_dir = case_dir / "nodes"
        node_dir.mkdir(parents=True, exist_ok=True)
        visual_rows = []
        for node_id in sorted(selected_ids, key=lambda value: (value not in cited_ids, value)):
            note = notes.get(node_id)
            if note is None or not getattr(note, "visual", False):
                continue
            data = base64.b64decode(note.content)
            digest = sha256(data)
            suffix = image_suffix(data)
            decoded = node_dir / f"{node_id}{suffix}"
            decoded.write_bytes(data)
            with Image.open(BytesIO(data)) as image:
                width, height = image.size
            source_paths, source_match_method, perceptual_distance = match_sources(data, sources)
            visual_rows.append({
                **retrieved.get(node_id, {"node_id": node_id, "retrieval_occurrences": []}),
                "node_id": node_id,
                "cited_by_classifier": node_id in cited_ids,
                "decoded_path": str(decoded),
                "sha256": digest,
                "width": width,
                "height": height,
                "source_paths": source_paths,
                "source_match_method": source_match_method,
                "perceptual_distance": perceptual_distance,
                "graph_summary": getattr(note, "context", ""),
                "graph_text_content": getattr(note, "text_content", ""),
            })
        make_contact_sheet(visual_rows, case_dir / "contact_sheet.jpg")
        packet = {
            "question_id": question_id,
            "question": question_row["question"],
            "reference": question_row["answer"],
            "main_doc": question_row["main_doc"],
            "documents": documents,
            "eight_b_answer": outcomes[question_id].get("candidate_answer"),
            "eight_b_answer_source": outcomes[question_id].get("candidate_source"),
            "thirty_two_b_answer": replay.get(question_id, {}).get("candidate_answer"),
            "thirty_two_b_verdict": replay.get(question_id, {}).get("judgment", {}).get("label"),
            "provisional_classification": classification,
            "visual_nodes": visual_rows,
        }
        (case_dir / "packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        inventory.append(packet)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "INVENTORY.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Prepared {len(inventory)} visual validation packets under {OUTPUT}")


if __name__ == "__main__":
    main()

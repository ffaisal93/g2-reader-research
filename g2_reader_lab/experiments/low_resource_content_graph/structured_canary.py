#!/usr/bin/env python3
"""Verify that the local VLM server enforces the two G2 JSON schemas."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from pathlib import Path

from jsonschema import Draft202012Validator
from openai import OpenAI


CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {"type": "array", "items": {"type": "string"}, "maxItems": 256},
        "summary": {"type": "string", "maxLength": 1200},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 32},
        "text_content": {"type": "string", "maxLength": 2400},
    },
    "required": ["keywords", "summary", "tags", "text_content"],
    "additionalProperties": False,
}

EVOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "suggested_connections": {
            "type": "array",
            "items": {"type": "integer"},
            "maxItems": 5,
        },
        "should_update": {"type": "boolean"},
        "new_summary": {"type": "string"},
        "new_keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "suggested_connections",
        "should_update",
        "new_summary",
        "new_keywords",
    ],
    "additionalProperties": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18000/v1")
    parser.add_argument("--model", default="local-qwen-vl")
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = OpenAI(base_url=args.base_url, api_key="local", timeout=300)
    cases = [
        (
            "content_analysis",
            CONTENT_SCHEMA,
            "Analyze this scientific text. The measured accuracy is 91.7 percent at 25 degrees C. "
            "Return keywords, one concise summary, tags, and text_content.",
        ),
        (
            "memory_evolution",
            EVOLUTION_SCHEMA,
            "The current node reports accuracy of 91.7 percent. Neighbor 4 gives the test conditions. "
            "Neighbor 7 discusses an unrelated dataset. Select useful connection IDs. Return the update decision.",
        ),
    ]

    jobs = [
        (repetition + 1, name, schema, prompt)
        for repetition in range(args.repetitions)
        for name, schema, prompt in cases
    ]

    def run_case(job):
        repetition, name, schema, prompt = job
        started = time.time()
        record = {"repetition": repetition, "case": name}
        try:
            response = client.chat.completions.create(
                    model=args.model,
                    messages=[
                        {"role": "system", "content": "Return only the required JSON object."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": name,
                            "strict": True,
                            "schema": schema,
                        },
                    },
                    temperature=0,
                    max_tokens=1536,
                    seed=42,
                )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            Draft202012Validator(schema).validate(parsed)
            record.update(
                {
                    "status": "valid",
                    "duration_sec": time.time() - started,
                    "finish_reason": response.choices[0].finish_reason,
                    "usage": response.usage.model_dump() if response.usage else None,
                    "response": parsed,
                }
            )
        except Exception as exc:
            record.update(
                {
                    "status": "invalid",
                    "duration_sec": time.time() - started,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(run_case, jobs))

    valid = sum(item["status"] == "valid" for item in results)
    report = {
        "model": args.model,
        "base_url": args.base_url,
        "requests": len(results),
        "concurrency": args.concurrency,
        "valid": valid,
        "invalid": len(results) - valid,
        "success_rate": valid / len(results) if results else 0,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("requests", "valid", "invalid", "success_rate")}))
    return 0 if valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

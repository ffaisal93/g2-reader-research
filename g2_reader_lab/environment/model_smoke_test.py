"""Run local-only embedding and text+image VLM smoke tests with measurements."""

from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path

import torch
from PIL import Image


def embedding_smoke(model_path: str) -> dict:
    from sentence_transformers import SentenceTransformer

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)
    started = time.perf_counter()
    model = SentenceTransformer(model_path, device="cuda", local_files_only=True)
    vector = model.encode(["G squared Reader embedding smoke test"], normalize_embeddings=True)[0]
    torch.cuda.synchronize()
    result = {
        "model_path": model_path,
        "dimensions": int(vector.shape[0]),
        "norm": float((vector @ vector) ** 0.5),
        "latency_seconds": time.perf_counter() - started,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(0),
    }
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return result


def vlm_smoke(model_path: str) -> dict:
    from qwen_vl_utils import process_vision_info
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)
    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, use_fast=False)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map="cuda",
        attn_implementation="eager",
    )
    image = Image.new("RGB", (112, 112), color=(255, 0, 0))
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "What is the dominant color? Answer with one word."},
            ],
        }
    ]
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[prompt], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    generated = generated[:, inputs.input_ids.shape[1] :]
    response = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
    torch.cuda.synchronize()
    return {
        "model_path": model_path,
        "dtype": "bfloat16",
        "prompt": "What is the dominant color? Answer with one word.",
        "response": response,
        "latency_seconds": time.perf_counter() - started,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vlm", required=True)
    parser.add_argument("--embedding", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "device": torch.cuda.get_device_name(0),
        "compute_capability": list(torch.cuda.get_device_capability(0)),
        "embedding": embedding_smoke(args.embedding),
        "vlm": vlm_smoke(args.vlm),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

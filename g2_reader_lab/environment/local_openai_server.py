"""Local-only OpenAI-compatible chat and embedding server for controlled runs."""

from __future__ import annotations

import argparse
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import torch
from fastapi import FastAPI
from lmformatenforcer import CharacterLevelParserConfig, JsonSchemaParser
from lmformatenforcer.integrations.transformers import (
    build_token_enforcer_tokenizer_data,
    build_transformers_prefix_allowed_tokens_fn,
)
from pydantic import BaseModel, ConfigDict


class Request(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: list[dict[str, Any]] | None = None
    input: str | list[str] | None = None
    max_tokens: int = 512
    temperature: float = 0.0
    response_format: dict[str, Any] | None = None


class Runtime:
    def __init__(self, vlm_path: str, embedding_path: str, max_visual_pixels: int, max_output_tokens: int, max_input_characters: int, max_json_array_length: int):
        from sentence_transformers import SentenceTransformer
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        self.lock = threading.Lock()
        self.max_visual_pixels = max_visual_pixels
        self.max_output_tokens = max_output_tokens
        self.max_input_characters = max_input_characters
        self.max_json_array_length = max_json_array_length
        self.processor = AutoProcessor.from_pretrained(vlm_path, local_files_only=True, use_fast=False)
        self.tokenizer_data = build_token_enforcer_tokenizer_data(self.processor.tokenizer)
        self.vlm = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            vlm_path,
            local_files_only=True,
            dtype=torch.bfloat16,
            device_map="cuda",
            attn_implementation="sdpa",
        )
        self.embedder = SentenceTransformer(embedding_path, device="cuda", local_files_only=True)

    def structured_output_prefix(self, response_format: dict[str, Any] | None):
        """Honor OpenAI JSON modes with token-level constrained decoding."""
        if not response_format:
            return None
        format_type = response_format.get("type")
        if format_type == "json_object":
            schema = None
        elif format_type == "json_schema":
            json_schema = response_format.get("json_schema", {})
            schema = json_schema.get("schema", json_schema)
        else:
            return None
        parser_config = CharacterLevelParserConfig(
            max_json_array_length=self.max_json_array_length
        )
        parser = JsonSchemaParser(schema, config=parser_config)
        return build_transformers_prefix_allowed_tokens_fn(self.tokenizer_data, parser)

    def chat(self, request: Request) -> dict[str, Any]:
        from qwen_vl_utils import process_vision_info

        messages = request.messages or []
        def truncate(value: str) -> str:
            if len(value) <= self.max_input_characters:
                return value
            half = self.max_input_characters // 2
            return value[:half] + "\n[SERVER_HEAD_TAIL_TRUNCATION]\n" + value[-half:]
        for message in messages:
            if isinstance(message.get("content"), str):
                message["content"] = truncate(message["content"])
            if isinstance(message.get("content"), list):
                normalized = []
                for item in message["content"]:
                    if item.get("type") == "image_url":
                        value = item.get("image_url")
                        url = value.get("url") if isinstance(value, dict) else value
                        normalized.append({"type": "image", "image": url, "max_pixels": self.max_visual_pixels})
                    else:
                        if item.get("type") == "text":
                            item = {**item, "text": truncate(str(item.get("text", "")))}
                        normalized.append(item)
                message["content"] = normalized
        with self.lock, torch.inference_mode():
            prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            images, videos = process_vision_info(messages)
            inputs = self.processor(
                text=[prompt],
                images=images or None,
                videos=videos or None,
                padding=True,
                return_tensors="pt",
            ).to("cuda")
            generation_limit = min(int(request.max_tokens), self.max_output_tokens)
            prefix_allowed_tokens_fn = self.structured_output_prefix(request.response_format)
            generated = self.vlm.generate(
                **inputs,
                max_new_tokens=generation_limit,
                do_sample=False,
                repetition_penalty=1.0,
                prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
            )
            completion = generated[:, inputs.input_ids.shape[1] :]
            text = self.processor.batch_decode(completion, skip_special_tokens=True)[0].strip()
        prompt_tokens = int(inputs.input_ids.numel())
        completion_tokens = int(completion.numel())
        eos_token_ids = self.vlm.generation_config.eos_token_id
        if isinstance(eos_token_ids, int):
            eos_token_ids = [eos_token_ids]
        last_token = int(completion[0, -1]) if completion_tokens else None
        hit_output_limit = completion_tokens >= generation_limit and last_token not in set(eos_token_ids or [])
        finish_reason = "length" if hit_output_limit else "stop"
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": prompt_tokens + completion_tokens, "peak_vram_bytes": int(torch.cuda.max_memory_allocated())},
        }

    def embeddings(self, request: Request) -> dict[str, Any]:
        texts = [request.input] if isinstance(request.input, str) else list(request.input or [])
        with self.lock:
            vectors = self.embedder.encode(texts, normalize_embeddings=True).tolist()
        return {
            "object": "list",
            "model": request.model,
            "data": [{"object": "embedding", "index": index, "embedding": vector} for index, vector in enumerate(vectors)],
            "usage": {"prompt_tokens": sum(len(text.split()) for text in texts), "total_tokens": sum(len(text.split()) for text in texts), "peak_vram_bytes": int(torch.cuda.max_memory_allocated())},
        }


def create_app(vlm_path: str, embedding_path: str, max_visual_pixels: int = 262144, max_output_tokens: int = 1024, max_input_characters: int = 20000, max_json_array_length: int = 256) -> FastAPI:
    state: dict[str, Runtime] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        state["runtime"] = Runtime(vlm_path, embedding_path, max_visual_pixels, max_output_tokens, max_input_characters, max_json_array_length)
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return {"object": "list", "data": [{"id": "local-qwen-vl", "object": "model"}, {"id": "local-bge-m3", "object": "model"}]}

    @app.post("/v1/chat/completions")
    def chat(request: Request) -> dict[str, Any]:
        torch.cuda.reset_peak_memory_stats()
        try:
            return state["runtime"].chat(request)
        finally:
            torch.cuda.empty_cache()

    @app.post("/v1/embeddings")
    def embeddings(request: Request) -> dict[str, Any]:
        torch.cuda.reset_peak_memory_stats()
        try:
            return state["runtime"].embeddings(request)
        finally:
            torch.cuda.empty_cache()

    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--vlm", required=True)
    parser.add_argument("--embedding", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--max-visual-pixels", type=int, default=262144)
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--max-input-characters", type=int, default=20000)
    parser.add_argument("--max-json-array-length", type=int, default=256)
    args = parser.parse_args()
    uvicorn.run(create_app(args.vlm, args.embedding, args.max_visual_pixels, args.max_output_tokens, args.max_input_characters, args.max_json_array_length), host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()

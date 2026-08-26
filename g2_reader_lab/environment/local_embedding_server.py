"""Small OpenAI-compatible embedding endpoint for local G² runs."""

from __future__ import annotations

import argparse
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    input: str | list[str]


def create_app(model_path: str, device: str = "cpu") -> FastAPI:
    state: dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        from sentence_transformers import SentenceTransformer

        state["model"] = SentenceTransformer(
            model_path,
            device=device,
            local_files_only=True,
        )
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [{"id": "local-bge-m3", "object": "model"}],
        }

    @app.post("/v1/embeddings")
    def embeddings(request: EmbeddingRequest) -> dict[str, Any]:
        texts = [request.input] if isinstance(request.input, str) else request.input
        started = time.time()
        vectors = state["model"].encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()
        return {
            "id": f"embd-{uuid.uuid4().hex}",
            "object": "list",
            "model": request.model,
            "data": [
                {"object": "embedding", "index": index, "embedding": vector}
                for index, vector in enumerate(vectors)
            ],
            "usage": {
                "prompt_tokens": sum(len(text.split()) for text in texts),
                "total_tokens": sum(len(text.split()) for text in texts),
                "duration_seconds": time.time() - started,
            },
        }

    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18001)
    args = parser.parse_args()
    uvicorn.run(
        create_app(args.model, args.device),
        host=args.host,
        port=args.port,
        workers=1,
    )


if __name__ == "__main__":
    main()

"""Environment-only bindings for running the frozen official source locally.

This module contains no retrieval, graph, planning, reasoning, or retry logic.
It only replaces the placeholder endpoints and paths shipped upstream.
"""

from __future__ import annotations

import os
from pathlib import Path


LAB_ROOT = Path(
    os.environ.get("G2_LAB_ROOT", str(Path(__file__).resolve().parents[3]))
).resolve()
VISDOM_ROOT = LAB_ROOT / "external" / "VisDoM"
PROCESSED_ROOT = LAB_ROOT / "data" / "processed_hf"

LLM_BASE_URL = os.environ.get("G2_LLM_BASE_URL", "http://127.0.0.1:18000/v1")
EMBED_BASE_URL = os.environ.get("G2_EMBED_BASE_URL", LLM_BASE_URL)
LLM_API_KEY = os.environ.get("G2_API_KEY", "local")
EMBED_API_KEY = os.environ.get("G2_EMBED_API_KEY", LLM_API_KEY)

MODELS = {
    "chat": os.environ.get("G2_CHAT_MODEL", "local-qwen-vl"),
    "embed": os.environ.get("G2_EMBED_MODEL", "local-bge-m3"),
    "eval": os.environ.get("G2_EVAL_MODEL", os.environ.get("G2_CHAT_MODEL", "local-qwen-vl")),
}

MEMORY_SYSTEMS_DIR = os.environ.get(
    "G2_MEMORY_DIR", str(LAB_ROOT / "results" / "official_trace" / "memory_systems")
)
PDF_TMP_DIR = os.environ.get(
    "G2_PDF_TMP_DIR", str(LAB_ROOT / "results" / "official_trace" / "pdf_tmp")
)
MAX_CONCURRENCY = int(os.environ.get("G2_MAX_CONCURRENCY", "1"))

DATASETS = {
    "spiqa": {
        "csv": str(VISDOM_ROOT / "spiqa" / "spiqa.csv"),
        "mineru_dir": str(PROCESSED_ROOT / "spiqa"),
        "key": "q_id",
        "docs_col": "documents",
    },
    "feta_tab": {
        "csv": str(VISDOM_ROOT / "feta_tab" / "feta_tab.csv"),
        "mineru_dir": str(PROCESSED_ROOT / "fetatab"),
        "key": "q_id",
        "docs_col": "documents",
        "encoding": "utf-8",
    },
    "scgqa": {
        "csv": str(VISDOM_ROOT / "scigraphvqa" / "scigraphqa.csv"),
        "mineru_dir": str(PROCESSED_ROOT / "scgqa" / "mineru_result"),
        "key": "q_id",
        "docs_col": "documents",
    },
    "paper_tab": {
        "csv": str(VISDOM_ROOT / "paper_tab" / "paper_tab.csv"),
        "mineru_dir": str(PROCESSED_ROOT / "papertab"),
        "key": "q_id",
        "docs_col": "documents",
    },
    "slidevqa": {
        "csv": str(VISDOM_ROOT / "slidevqa" / "slidevqa.csv"),
        "mineru_dir": str(PROCESSED_ROOT / "slide"),
        "key": "q_id",
        "docs_col": "documents",
    },
}

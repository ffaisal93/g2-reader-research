from __future__ import annotations

import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "G2_Reader_patched"))

os.environ.setdefault("G2_LLM_BASE_URL", "http://127.0.0.1:18000/v1")
os.environ.setdefault("G2_CHAT_MODEL", "local-qwen-vl")
os.environ.setdefault("G2_EMBED_MODEL", "local-bge-m3")

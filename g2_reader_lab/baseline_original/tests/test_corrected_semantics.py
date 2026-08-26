from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from agent_search.bm25 import rank_bm25
from agent_search.pred_kw import DAGPred


def predictor() -> DAGPred:
    value = object.__new__(DAGPred)
    value.args = SimpleNamespace(save_dir="", max_context_tokens=6)
    value.logger = None
    return value


def test_bm25_uses_length_normalized_term_frequency():
    documents = ["alpha", "alpha " + "noise " * 100, "beta"]
    assert rank_bm25(documents, ["alpha"], k=2, return_indices=True) == [0, 1]


def test_query_context_limit_is_configurable_and_preserves_ends():
    class Tokenizer:
        def encode(self, text):
            return text.split()

        def decode(self, values):
            return " ".join(values)

    class Client:
        class Completions:
            @staticmethod
            def create(**kwargs):
                assert kwargs["messages"][0]["content"] == "a b c h i j"
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                    usage=None,
                )

        chat = SimpleNamespace(completions=Completions())

    result = predictor().query_llm("a b c d e f g h i j", "model", Tokenizer(), Client(), track_usage=False)
    assert result == "ok"


def test_visual_notes_are_included_in_reading_order_initialization_source():
    source = Path(__file__).parents[1] / "G2_Reader_patched" / "prebuild" / "amem_new.py"
    text = source.read_text(encoding="utf-8")
    assert "ordered_notes = list(ms.memories.values())" in text
    assert "j < len(ordered_notes)" in text


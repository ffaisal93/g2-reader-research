"""Focused reproductions for blockers in the pinned released implementation.

These tests intentionally fail against the pristine checkout. They are run against the
separate patched worktree while each smallest repair is applied.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PATCHED_ROOT = Path(__file__).parents[1] / "G2_Reader_patched"
sys.path.insert(0, str(PATCHED_ROOT))

from agent_search.pred_kw import DAGPred  # noqa: E402
from prebuild.memory_layer import AgenticMemorySystem  # noqa: E402
from scripts.evaluate import Evaluator  # noqa: E402


class NullLogger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


def bare_predictor() -> DAGPred:
    predictor = object.__new__(DAGPred)
    predictor.logger = NullLogger()
    predictor.args = SimpleNamespace(top_k=5, save_dir="unused")
    return predictor


def test_evolution_call_accepts_its_callers_max_tokens_argument() -> None:
    signature = inspect.signature(AgenticMemorySystem._call_llm_evolve)
    assert "max_tokens" in signature.parameters


def test_dag_validator_enforces_maximum_depth() -> None:
    predictor = bare_predictor()
    dag = {
        "nodes": [
            {"id": "root", "task": "root", "children": ["n1"]},
            {"id": "n1", "task": "one", "children": ["n2"]},
            {"id": "n2", "task": "two", "children": ["n3"]},
            {"id": "n3", "task": "three", "children": []},
        ]
    }
    assert predictor._validate_dag(dag, max_depth=3, max_nodes=8) is False


def test_dag_validator_rejects_duplicate_ids_and_missing_children() -> None:
    predictor = bare_predictor()
    duplicate = {
        "nodes": [
            {"id": "root", "task": "root", "children": []},
            {"id": "root", "task": "duplicate", "children": []},
        ]
    }
    missing = {"nodes": [{"id": "root", "task": "root", "children": ["absent"]}]}
    assert predictor._validate_dag(duplicate, max_depth=3, max_nodes=8) is False
    assert predictor._validate_dag(missing, max_depth=3, max_nodes=8) is False


def test_dependency_execution_runs_children_before_parent() -> None:
    predictor = bare_predictor()
    predictor.node_results = {}
    observed: list[str] = []

    def execute(node_id, *_args, adjust_round=0, **_kwargs):
        observed.append(node_id)
        predictor.node_results[(adjust_round, node_id)] = f"answer:{node_id}"

    predictor._execute_dag_node = execute
    predictor._check_evidence_sufficiency = lambda *_args, **_kwargs: (True, [])
    predictor.reasoner_with_trajectory = lambda *_args, **_kwargs: ("<output>ok</output>", "prompt")
    predictor.save_model_responses_to_folders = lambda *_args, **_kwargs: None

    dag = {
        "nodes": [
            {"id": "root", "task": "root", "type": "question", "children": ["parent"]},
            {"id": "parent", "task": "parent", "type": "subquestion", "children": ["leaf"]},
            {"id": "leaf", "task": "leaf", "type": "subquestion", "children": []},
        ]
    }
    response = predictor._execute_dag(
        dag,
        "question",
        "model",
        None,
        None,
        "context",
        "id",
        0,
        {"_id": "id"},
        [],
        max_adjust_rounds=0,
    )
    assert response == "<output>ok</output>"
    assert observed == ["leaf", "parent"]


@pytest.mark.parametrize("tag", ["output", "answer"])
def test_evaluator_accepts_configured_generation_tags(tag: str) -> None:
    evaluator = object.__new__(Evaluator)
    assert evaluator.extract_model_answer(f"<{tag}>42</{tag}>") == "42"


def test_dag_logging_does_not_require_unreleased_judge_field() -> None:
    source = inspect.getsource(DAGPred.get_pred_dag)
    assert "item['judge']" not in source

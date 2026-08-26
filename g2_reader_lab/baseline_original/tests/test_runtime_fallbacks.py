from __future__ import annotations

from types import SimpleNamespace

from agent_search.pred_kw import DAGPred


class NullLogger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


def predictor() -> DAGPred:
    value = object.__new__(DAGPred)
    value.logger = NullLogger()
    value.args = SimpleNamespace(save_dir="unused")
    value.decomposer_dag_prompt = "$DOC$ $Q$"
    value.dag_decomposer_after_check_prompt = "$DOC$ $Q$ $EVIDENCE$ $GAPS$ $OLD_DAG$"
    value.query_llm = lambda *_args, **_kwargs: "not json"
    return value


def test_invalid_planning_output_has_bounded_single_node_fallback():
    result = predictor().dag_decomposer("context", "question", "model", None, None)
    assert result["fallback"] == "invalid_structured_output"
    assert result["nodes"] == [{"id": "root", "task": "question", "type": "question", "children": []}]


def test_invalid_refinement_retains_previous_graph():
    old = {"nodes": [{"id": "root", "task": "question", "children": []}]}
    result = predictor().dag_decomposer_after_check(
        "context", "question", [], ["gap"], "model", None, None, old_dag=old
    )
    assert result is old

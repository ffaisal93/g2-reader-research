# Controlled comparison report

## Outcome

The corrected released path and independently structured minimal path both completed one real local-model question with complete machine- and human-readable traces. They returned the same incorrect answer (`1`; reference count `4`). This validates executable plumbing, observability, evaluation, and artifact production—not benchmark reproduction.

The comparison cannot yet be called controlled at benchmark scale. Although the model checkpoints, serving envelope, input question, processed document, and retrieval budget matched, runtime graph states diverged (11 versus 13 nodes), the planning trajectories diverged (upstream fallback versus a nine-node minimal plan), and only the upstream run reused an offline graph cache. These differences are reported rather than tuned away.

## Execution findings

- The corrected upstream planner emitted a syntactically valid but semantically invalid dependency graph on all three attempts (a referenced child was absent). Strict validation rejected it and the documented single-node fallback completed the question.
- The clean planner produced a valid nine-node DAG and executed children before parents. Four rounds generated 36 inspectable Worker answers before bounded termination.
- Both systems retrieved evidence pointing at a chart/rank table rather than counting the four 1979 catalogue entries required by the reference.
- The clean checker returned `gaps` as a scalar string. Trace inspection revealed that it was split into characters; this was corrected after the run with a focused regression test. Prior artifacts were not overwritten.
- The final serving profile is BF16/SDPA with 20,000 input characters, a 262,144-pixel visual cap, 1,024 output tokens, expandable CUDA segments, and per-request CUDA cache cleanup.

## Validation status

The normal suite passes 34 tests after the checker regression was added. Python compilation, configuration parsing, GPU tensor execution, real VLM image inference, real embedding inference, selective-data validation, graph serialization, baseline trace rendering, and one-question real inference all pass.

The formal 15-question smoke and 100-question mini comparisons remain incomplete. The smoke graph has 5,804 nodes and requires at least 23,216 VLM graph calls for three evolution rounds (up to 69,648 attempts with retries), excluding online inference. This is the concrete resource limitation; no aggregate accuracy or paper-scale claim is made.

See `results/comparisons/smoke_comparison.md`, `results/comparisons/mini_comparison.md`, and `results/comparisons/per_question.jsonl` for the immutable result artifacts.

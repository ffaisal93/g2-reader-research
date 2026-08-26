# Released G²-Reader runtime audit

Audited revision: `e4d047a756ef9136ea7f0c4dd8ba36eb1b08ec27`. The checkout under `external/G2_Reader` is pristine. Repairs live only in the linked worktree `baseline_original/G2_Reader_patched`.

The runtime path was followed from `scripts/G2reader.sh` through `scripts/test_rag.py`, `DAGPred.main`, initial retrieval, memory construction/evolution, Planning Graph generation, dependency execution, evidence checking/refinement, synthesis, and evaluation.

| ID | Severity | Location | Observed failure or discrepancy | Minimal correction | Architectural effect |
|---:|---|---|---|---|---|
| 1 | Blocker | `prebuild/memory_layer.py::_call_llm_evolve` | Caller supplies `max_tokens`, callee rejected it; the broad catch returned the unchanged note, silently disabling evolution. | Accept and forward `max_tokens`; keep failure propagation inside the call. | Restores intended Content Graph evolution. |
| 2 | Blocker | `agent_search/pred_kw.py::_execute_dag` | Edges are parent-to-child, but Kahn order executed parents before the child answers they consume. | Reverse the validated topological order. | Restores intended hierarchical dependency reasoning. |
| 3 | Blocker | `DAGPred.get_pred_dag` | Logging indexed `item['judge']`, but released processed rows do not contain that field. | Use `item.get('judge')`. | None; prevents post-inference crash. |
| 4 | Major | `scripts/evaluate.py::extract_model_answer` | Generation prompts require `<output>`, while evaluation accepted only `<answer>`. | Accept both tags during compatibility evaluation. | None; syntax interoperability only. |
| 5 | Major | `prebuild/amem_new.py::construct_memory` | Reading-order links were initialized only for text notes; visual nodes began disconnected. | Apply the configured window to every retained node. | Restores multimodal graph connectivity, though released extraction still groups modalities rather than preserving original interleaving. |
| 6 | Major | `DAGPred.query_llm` | A hard-coded 4,096-token limit discarded the prompt center without telemetry. | Add a configurable 20,000-token default and log any explicit head-tail truncation. | Changes usable context budget; policy is now visible and shared by comparison configs. |
| 7 | Major | `retriever_split_sem_bm25` | The path labeled BM25 was regex phrase counting (`unique + 0.01 × frequency`), without IDF or length normalization. | Route it through a dependency-free standard BM25 scorer. | Corrects lexical retrieval semantics. |
| 8 | Blocker | `_validate_dag` | `max_depth` was accepted but never enforced; duplicate IDs and missing endpoints were also not rejected directly. | Validate node identity/endpoints and enforce computed depth. | Enforces the prompted Planning Graph contract. |
| 9 | Major | `_execute_dag` refinement | Each revised graph reruns wholesale and final synthesis previously used only the last round. | Keep whole-graph reruns for fidelity, but retain all round answers in synthesis and trace. | Evidence is no longer silently discarded; no selective caching improvement was added. |
| 10 | Architectural discrepancy | retrieval/Worker handoff | Structured Content Graph IDs and edges collapse into `Related Memory` text plus images before Worker inference. | Preserve this evidence interface for a fair comparison; record explicit node/edge selections in traces in the clean implementation. | No baseline prompt advantage is introduced. |
| 11 | Blocker | shell scripts and imports | The launcher referenced `/data/new`, `test.test_rag`, a placeholder model, and optional scripts have unresolved imports. | Correct the main launcher to repository-relative paths, `scripts.test_rag`, and required `G2_MODEL`; document unsupported optional entry points. | None for the primary released pipeline. |

## Audit conclusions

Five defects could prevent a documented run or invalidate its output directly (1, 2, 3, 8, 11). Items 4–7 and 9 alter evaluation, graph construction, context, retrieval, or evidence retention enough to affect reported results. Item 10 is an architectural limitation rather than a crash and is intentionally held constant in the primary comparison.

See `additional_runtime_findings.md` for six further defects found only after executing the full local runtime path.

The released code also uses broad exception handling in several preprocessing paths. The corrected baseline does not redesign those paths; targeted regression tests ensure the confirmed silent evolution failure cannot recur.


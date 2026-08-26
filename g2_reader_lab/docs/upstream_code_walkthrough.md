# Released runtime walkthrough

This walkthrough describes the pinned `external/G2_Reader` revision and identifies corrected-worktree behavior where execution requires it.

## Runtime path

1. **Dataset row and document resolution.** `scripts/test_rag.py` reads JSONL rows and invokes `DAGPred.main`. `prebuild/amem_new.py::load_dataset_df` loads the matching released CSV; `resolve_docs_from_dataset_mineru` maps the question ID to MinerU directories. The corrected path normalizes prefixed IDs and makes the document cap explicit.
2. **MinerU parsing.** `utils/mineru_utils.py` reads each `_content_list.json`. Text is accumulated into overlapping chunks; figure/table entries resolve their image paths and neighboring context. Missing files are reported or skipped by the released preprocessing helpers.
3. **Node analysis.** `construct_memory` sends text or image payloads through the analysis prompts and creates `MemoryNote` objects containing content, keywords, context, tags, and modality. Calls are asynchronous but bounded by the corrected runtime semaphore.
4. **Embeddings and initial links.** BGE embeddings are requested from the configured OpenAI-compatible endpoint. Reading-order neighbors are added within the configured window for all retained modalities in the corrected baseline.
5. **Content Graph evolution.** `AgenticMemorySystem.add_note` retrieves semantic candidates, calls the evolution prompt, updates existing notes, and adds valid suggested links. The corrected signature forwards `max_tokens`; failures remain logged and fall back to the unchanged note.
6. **Initial retrieval.** `search_memory` dispatches semantic, lexical BM25, or combined retrieval. The returned graph neighborhood is flattened into `Related Memory` text and image payloads before Worker inference.
7. **Planning Graph generation.** `DAGPred.dag_decomposer` prompts for a JSON graph. The corrected parser accepts tagged, fenced, or plain JSON, then `_validate_dag` rejects duplicate IDs, dangling endpoints, cycles, and excess depth.
8. **Dependency execution.** An edge `parent -> child` means the parent consumes the child answer. `_execute_dag` therefore executes reverse topological order, retrieves evidence for each node, and calls the Worker with direct child answers plus flattened retrieved evidence.
9. **Evidence checking and refinement.** The evidence-check prompt labels the trajectory sufficient or insufficient. An insufficient judgment triggers a revised Planning Graph and a bounded whole-graph rerun. The corrected path retains every round for final synthesis.
10. **Final reasoning.** The trajectory-aware reasoner receives the original question and accumulated round answers and emits the requested tagged output. Context truncation is configurable and logged.
11. **Evaluation.** `scripts/evaluate.py` normalizes model answers and computes released task metrics. The compatibility extractor accepts both `<output>` and `<answer>`.

## State, persistence, and failures

- Content Graph caches are serialized by released memory code; inference results are JSONL under the configured result directory.
- The patched run adds configuration through `config/local_runtime.py`; credentials come from environment variables and are never stored in results.
- Analysis/evolution retains released fallback semantics but logs malformed output. Planning Graph structure is strictly validated.
- The primary launcher is repository-relative. Optional preprocessing/single-VLM scripts are outside the validated runtime and retain optional dependency assumptions.

Detailed classifications and repairs are in `upstream_audit.md` and `baseline_repairs.md`.
Additional execution-only findings are recorded in `additional_runtime_findings.md`.

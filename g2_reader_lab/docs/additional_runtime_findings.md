# Additional defects discovered by execution

The first real local-model run exposed six issues beyond the eleven suspected findings in `upstream_audit.md`.

| ID | Severity | Location | Finding | Correction |
|---:|---|---|---|---|
| 12 | Blocker | `prebuild/amem_new.py` dataset lookup | Released rows use prefixed IDs such as `feta_tab_10447`, while the source CSV uses numeric IDs. | Normalize the known dataset prefix before lookup. |
| 13 | Major | `resolve_docs_from_dataset_mineru` | A hard-coded `[:5]` silently restricted every question to five documents. | Add explicit `--document_limit`; zero means all released documents. |
| 14 | Blocker | `prebuild/amem_new.py::embed_one` | `embed_aclient` was called but never initialized. | Initialize a separate embedding client from configurable endpoint/key values. |
| 15 | Interoperability | Structured-output parsing | Local Qwen sometimes emits fenced JSON or JSON containing literal control characters. | Centralize tagged/fenced/plain extraction and tolerate control characters while retaining strict graph-schema validation. |
| 16 | Major | Content Graph cache path | The released cache key ignored document scope and the writer could persist to a different path than the loader checked, allowing stale cross-run graph reuse. | Use one explicit cache key containing question ID, document limit, and evolution rounds for both reads and writes. |
| 17 | Major | `prebuild/amem_new.py::construct_memory` | The released snapshot omitted explicit graph edges and retained raw content, making audit and safe comparison difficult. | Persist a redacted node/summary/tag snapshot plus explicit ID edges in the scoped cache. |

The current one-document run also demonstrates a model/profile limitation rather than a code defect: the shared 7B model frequently violates the upstream analysis JSON format. The corrected baseline logs each failure and uses released-style defaults; the clean implementation uses bounded retries with explicit traceable fallbacks. Accuracy comparisons must report these fallback counts.

# Paper versus released code

The eleven requested hypotheses were traced through the pinned runtime. The authoritative finding table is in `upstream_audit.md`.

Five are execution blockers in the released path: the evolution signature mismatch, reversed dependency execution, mandatory missing `judge`, incomplete DAG validation, and unusable launcher/module defaults. Four major discrepancies affect reported behavior: evaluator tag mismatch, text-only initial links, silent 4,096-token center truncation, and non-BM25 lexical scoring. Refinement also discarded earlier rounds. The explicit Content Graph is flattened before Worker generation; this is a confirmed architectural discrepancy rather than a crash.

The corrected baseline changes only behavior required to execute the intended architecture. It does not add explicit graph edges to Worker prompts, selective refinement caching, new tools, or dataset-specific tuning. Four additional defects found during real execution are recorded in `upstream_audit.md`.

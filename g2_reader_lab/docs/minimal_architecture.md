# Clean minimal architecture

The readable implementation lives in `minimal_g2_reader/src/minig2` and uses two distinct directed graphs.

The **Content Graph** contains ordered coarse text chunks and visual elements. Reading-order edges cover every modality. Model-suggested links are schema-validated, limited to existing IDs, and bounded. Query retrieval fills an exact node budget deterministically and records the selected induced edges and reasons.

The **Planning Graph** uses `parent -> child` to mean that the parent depends on the child. Validation rejects duplicates, missing endpoints, cycles, excess nodes, and excess depth. Execution is child-first; each Worker receives raw retrieved evidence and direct prerequisite answers. Explicit relationships are written to traces but withheld from Worker prompts to match the corrected upstream evidence interface.

Structured-output attempts are bounded. Failures are explicit in traces; graph construction has deterministic traceable fallbacks so one malformed response does not discard an experiment. Every refinement round is retained for synthesis.

Typed dataclasses define boundaries; construction, retrieval, planning, agents, orchestration, evaluation, and tracing are separate modules. Unit tests use scripted models and hashing embeddings. Real profiles use the same local Qwen2.5-VL-7B-Instruct and BGE-M3 endpoint as the corrected baseline.
## Future modular extension points

A future capability adapter may consume one `PlanningNode` plus its `RetrievedEvidence` Content subgraph and return a typed, source-grounded result. Reserved interfaces are table-relational execution, scientific semantic interpretation, chart/figure interpretation, cross-page/slide alignment, numerical verification, and an evidence ledger for provenance-constrained generation. No adapter is implemented or invoked in this baseline.

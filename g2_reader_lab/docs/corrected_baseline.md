# Corrected released baseline

The corrected baseline is a linked worktree at `baseline_original/G2_Reader_patched`, pinned to the same commit as the pristine source. Its diff is intentionally narrow and reviewable.

## Validation

Run:

```bash
cd baseline_original/G2_Reader_patched
../../.venv/bin/python -m pytest ../tests -q
```

The suite covers evolution-call compatibility, strict Planning Graph limits, dependency execution, answer-tag interoperability, absent `judge` metadata, genuine BM25 behavior, configurable truncation, and visual reading-order initialization.

## Runtime configuration

The main launcher now requires `G2_MODEL` rather than embedding a placeholder. API endpoint, API key, embedding endpoint, model IDs, dataset paths, graph parameters, and concurrency must be supplied through the versioned experiment profile and environment. Secrets are never written to traces or configuration.

The corrected baseline preserves the released Worker's raw evidence format. It does not receive explicit graph relationships that the original did not receive. The clean implementation records explicit induced subgraphs for inspection but follows the same restriction during primary generation.

## Known limitations

- Processed MinerU artifacts remain required for released preprocessing.
- Refined Planning Graphs rerun as a whole; selective caching is intentionally not introduced.
- The upstream parser collects text and visual elements separately, so connecting every node does not reconstruct exact page interleaving.
- Qwen3-VL-32B is unavailable locally and is not claimed to fit the V100 safely. Controlled comparison uses Qwen2.5-VL-7B-Instruct for both methods.

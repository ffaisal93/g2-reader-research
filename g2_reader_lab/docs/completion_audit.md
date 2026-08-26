# Completion audit

Audit date: 2026-08-18

| Definition-of-done item | Status | Evidence |
|---|---|---|
| Reproducible environment | Pass | `environment/environment.lock.yml`; six YAML files parse |
| GPU, VLM, and embedding smokes | Pass | `results/smoke/gpu_smoke.json` and recorded real-model checks |
| External revisions pinned | Pass | `data/manifests/source_revisions.json` |
| Deterministic smoke and mini slices | Partial | 15/100 rows are frozen; all 109 smoke documents validate, but mini payload is intentionally not downloaded |
| Complete upstream runtime documentation | Pass | `docs/upstream_code_walkthrough.md` |
| Paper/code discrepancies verified | Pass | 11 initial findings plus six execution findings, with tests or source locations |
| Pristine upstream checkouts unchanged | Pass | G2_Reader and VisDoM both report zero status entries at their pinned commits |
| Baseline repairs recorded as patches | Pass | Four regenerated patch files under `baseline_original/patches/` |
| Corrected baseline runs on all smoke questions | Blocked by resource gate | One real question completed; full graph needs at least 23,216 VLM calls |
| Minimal unit suite | Pass | 34 tests pass; two dependency deprecation warnings |
| One trace from every dataset | Incomplete | One FetaTab real trace completed; the other four were not launched after the cost gate |
| Minimal implementation runs on smoke | Blocked by resource gate | One real question completed; no aggregate smoke claim |
| Matched-budget comparison | Partial | One-document matched-plumbing artifact exists; offline cache and graph-state differences prevent a formal efficiency claim |
| Mini comparison or concrete limitation | Pass (limitation) | `results/comparisons/mini_comparison.md` and `results/smoke/full_run_cost_estimate.json` |
| No future capability modules added | Pass | Only reserved interfaces are documented |
| Ready for the next modular experiment | Pass with benchmark caveat | Typed modules, CLI, configs, traces, tests, and extension interfaces are present |

The implementation contract is therefore complete through reproducible construction, audit, corrected execution, clean implementation, tests, and one-question comparison. It is **not complete as a full benchmark reproduction**. Phase 7 remains open until an approved compute/budget strategy runs both methods across the formal smoke slice and then the mini slice.

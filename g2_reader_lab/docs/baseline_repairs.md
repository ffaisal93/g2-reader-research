# Baseline repair ledger

Pristine reference: `external/G2_Reader` at `e4d047a756ef9136ea7f0c4dd8ba36eb1b08ec27`. Corrected linked worktree: `baseline_original/G2_Reader_patched`.

| Repair | Original behavior | Failing check | Corrected behavior | Architecture change |
|---|---|---|---|---|
| Evolution call | Unexpected `max_tokens` was caught and evolution was lost. | Evolution compatibility test. | Argument is accepted and forwarded. | None. |
| Dependency order | Parents ran before required children. | Execution-order test. | Reverse topological traversal. | Restores prompted semantics. |
| Missing judge | Successful inference could crash while logging. | Missing-field test. | Optional lookup. | None. |
| Answer tags | `<output>` could not be scored. | Extraction test. | Accept both released tags. | None. |
| Reading links | Visual nodes began disconnected. | Visual-link test. | All modalities receive reading links. | Restores multimodal intent. |
| Context budget | Fixed 4,096 head/tail truncation was silent. | Truncation test. | Configurable budget with telemetry. | Explicit controlled budget. |
| Lexical retrieval | Phrase frequency was labeled BM25. | Ranking test. | Standard dependency-free BM25. | Corrects stated retrieval method. |
| DAG validation | Depth, identity, and endpoints were incomplete. | Invalid-graph tests. | Strict bounded DAG validation. | Enforces contract. |
| Refinement evidence | Only the last round reached synthesis. | Trajectory test. | All rounds retained and traced. | Prevents evidence loss. |
| Launcher | Absolute paths and placeholder module/model failed. | Shell inspection/reproduction. | Repository-relative launcher and required model. | None. |
| Runtime data/client | Prefixed IDs, five-doc cap, and missing embedding client blocked or changed runs. | Real one-question run. | Normalize ID, expose cap, initialize client. | Removes hidden cap. |
| Structured syntax | Fenced/control-character JSON failed parsing. | Parser tests. | Tolerant extraction plus strict schema validation. | Interoperability only. |
| Cache scope and snapshot | Cache reads and writes used inconsistent, under-scoped paths; snapshots lacked explicit redacted edges. | Real cache-reuse reproduction. | One scoped key is used for both operations and a redacted node/edge graph is persisted. | Provenance and reproducibility only. |
| Invalid planning output | Repeated schema-invalid planner output aborted execution or left behavior implicit. | Real 7B planning run. | Three strict attempts are traced, then a labeled single-node fallback completes the path; invalid refinements retain the old valid DAG. | Explicit availability fallback. |
| Runtime telemetry | Endpoint calls and peak VRAM were not present in the question artifact. | Trace completeness check. | Record model usage, endpoint-reported peak VRAM, planning rounds, execution orders, retrieval IDs, checks, and trajectories. | Observability only. |

Run `.venv/bin/python -m pytest baseline_original/tests -q` from the lab root. Patch files under `baseline_original/patches/` are the reviewable record; the pristine checkout remains clean.

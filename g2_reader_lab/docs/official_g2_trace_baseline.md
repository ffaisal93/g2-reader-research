# Official G²-Reader Trace Baseline

## Scope

This experiment studies the released G²-Reader implementation before any
local-repair method is introduced. Minimal G² and the previously patched
official worktree are excluded from the primary evidence condition.

## Frozen source

- Upstream: `https://github.com/DorothyDUUU/G2_Reader.git`
- Commit: `e4d047a756ef9136ea7f0c4dd8ba36eb1b08ec27`
- Clean reference: `external/G2_Reader`
- Trace worktree: `baseline_original/G2_Reader_official_trace`
- Local chat model: Qwen3-VL-32B-Instruct-FP8 served as `local-qwen-vl`
- Local embedding model: BGE-M3 served as `local-bge-m3`
- GPU for the pilot: NVIDIA L40S, 46,068 MiB visible memory

The model stack differs from the paper-scale configuration. Results must be
attributed to the released code under this local model stack, not presented as
a reproduction of the paper's headline accuracy.

## Permitted local changes

The trace worktree may contain only:

1. environment bindings replacing released placeholder URLs, credentials, and
   paths;
2. best-effort passive event recording;
3. experiment launch and artifact-manifest utilities outside the core runtime;
4. behavior-neutral released-code repairs required to obtain valid artifacts
   (defined and logged below);
5. bounded error-only transport/structured-output recovery that does not run
   after a successful call.

The trace must not change successful-call prompts, retrieval results, graph
construction, Planning Graph validation, execution order, refinement limits,
Worker inputs, checker interpretation, or final synthesis. An invalid or
length-truncated preprocessing response receives one compact JSON-schema retry
enforcing `keywords`, `summary`, `tags`, and the `text_content` field required
by the released image-note consumer. This exception is recorded and applies
only where released code would otherwise silently insert a failure placeholder
into the Content Graph.

## Current trace additions

`config/local_runtime.py` maps the released placeholders to environment-driven
local endpoints and existing VisDoM/MinerU paths. It is enabled only when
`G2_USE_LOCAL_RUNTIME=1`.

The Qwen3 vLLM server supports continuous batching. The fixed audit condition
uses eight concurrent preprocessing requests and a 3,600-second client
transport timeout. The model server exposes a 24,000-token context limit. The
effective concurrency, timeout, model and seed are serving-stack parameters,
not claimed as paper defaults.

Every preprocessing, evolution, Planning Graph, Worker, evidence-check and
final-synthesis chat request sends seed 42. A structured preprocessing retry,
if needed after invalid/truncated JSON, sends seed 43 so replay behavior is
explicit and stable. `PYTHONHASHSEED` is also fixed at 42. Continuous batching
means this is a fixed-seed experiment, not a claim of byte-identical decoding.

`agent_search/passive_trace.py` appends JSONL events and swallows trace I/O
errors so observability cannot terminate the G² execution.

`agent_search/pred_kw.py` records:

- question start/end;
- complete non-image model prompts and raw responses;
- model purpose, decoding parameters, token counts, attempts, and latency;
- successful Planning Graphs and actual execution orders;
- Worker task, textual context, child IDs, response, round, and image count;
- raw and parsed sufficiency-check responses;
- Content Graph node IDs in semantic retrieval logs.

Images are not duplicated into the event log. They remain recoverable from
the persisted Content Graph/memory system and processed source assets.

## Behavior-neutral runtime repairs required for a valid run

The released source could not produce a trustworthy local artifact without
four small repairs. Each observed invalid run and its evidence is retained in
`results/official_trace/audits/OFFICIAL_RUNTIME_BLOCKERS.md`.

- bind the otherwise undefined asynchronous embedding client to the configured
  BGE-M3 endpoint;
- pass the already supplied `max_tokens` evolution argument through the callee;
- load the exact saved `<question_id>_iter_<round>` graph directory;
- treat retriever construction exceptions as question failures and make the
  optional `judge` field safe in final logging.

None changes a successful model prompt, retrieval ranking, graph algorithm,
Planning Graph, Worker answer, sufficiency decision or final synthesis.

## Released behaviors preserved for diagnosis

The following observations are properties of the frozen upstream source and
are intentionally not repaired in this condition:

- dataset lookup takes at most the first five listed documents;
- initial and refined Planning Graph generation can make up to five attempts
  in each of three recursive rounds before raising an exception;
- `_validate_dag` receives a depth bound but does not enforce it;
- Planning Graph edges are traversed in parent-to-child topological order even
  though a parent attempts to consume its children's existing answers;
- the root is skipped during Worker execution;
- insufficient evidence can trigger up to three complete adjustment rounds;
- final synthesis uses only the final round's Worker results;
- an unrecovered structured-output failure terminates the question; there is no
  semantic fallback or fabricated replacement evidence in an eligible run.

These are hypotheses about potential failure mechanisms, not frequency claims.
The pilot and 100-question audit will measure their observed consequences.

## Evidence protocol

For each incorrect completed question, annotation records the earliest/root
failure and all downstream events. Root categories are retrieval, Worker
support, decomposition, composition, source-unverifiable, and runtime/parsing.
False sufficiency and propagation are independent flags rather than mutually
exclusive root categories.

No repair will be implemented until the frozen audit has measured the dominant
repairable Worker-support failure.

## Pilot diagnostics

`pilot_v1` was stopped and excluded after the released concurrency of ten met
the local server's serialized generation lock: one of 149 concurrently
scheduled text-analysis requests exceeded the SDK timeout after more than 30
minutes, while other submitted requests remained queued. `pilot_v2` was a
startup-only instrumentation failure caused by a missing standard-library
import and performed no graph or model work. `pilot_v3` is the first eligible
clean pilot, using concurrency one, the extended transport timeout, and a fresh
memory directory on a freshly restarted server.

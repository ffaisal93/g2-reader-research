# Low-Resource G2 Content Graph Experiment Report

## 1. Objective

Build the G2 Content Graph in less than 180 seconds on one NVIDIA L40S.

Do not accept a measurable decrease in retrieval quality or final QA accuracy.

Keep the official traced implementation unchanged. Use it as the teacher and control.

## 2. Experiment sequence

Run one fixed example first. Use `spiqa_58`.

Expand the experiment only after the first example passes its latency and quality gates.

The experiment sequence is:

1. Reuse the completed Qwen3-VL-32B teacher baseline.
2. Validate strict JSON output with Qwen3-VL-8B-Instruct-FP8.
3. Build one complete student Content Graph.
4. Apply behavior-preserving construction changes.
5. Build the same graph again.
6. Compare graph construction, retrieval, and final QA results.
7. Expand to more examples only if the first example passes.

## 3. Fixed control conditions

- Question ID: `spiqa_58`
- Document limit: 5
- Teacher model: `Qwen3-VL-32B-Instruct-FP8`
- Student candidate: `Qwen3-VL-8B-Instruct-FP8`
- Embedding model: `bge-m3`
- Evolution rounds: 1
- Random seed: 42
- Retrieval budget: 5
- Teacher source: `baseline_original/G2_Reader_official_trace`

## 4. Existing teacher baseline

The teacher baseline is complete. It does not require another 32B build.

Measured teacher results:

- Documents loaded: 5
- Content Graph nodes: 182
- Total construction and query duration: 3,360.84 seconds
- Text-analysis calls: 130
- Image-analysis calls: 53, including one retry
- Evolution calls: 182
- Total VLM calls: 365
- Total VLM tokens: 2,263,224
- Explicit embedding tokens: 45,916
- Text-analysis wall time: 474.72 seconds
- Image-analysis wall time: 652.37 seconds
- Evolution wall time: 1,959.69 seconds
- Explicit embedding wall time: 141.07 seconds

Teacher artifacts:

- `results/official_trace/audits/qwen3_official_fixedseed_pilot5_v8/questions/spiqa_58/`
- `results/official_trace/memory_systems_qwen3_official_fixedseed_v5/spiqa_58_iter_0/`
- `results/official_trace/memory_systems_qwen3_official_fixedseed_v5/spiqa_58_iter_1/`

## 5. Acceptance gates

The student server must satisfy these conditions before a graph build:

- JSON parse success: 100 percent
- JSON Schema success: 100 percent
- Invalid connection IDs: 0
- Truncated responses: 0

The one-example graph must satisfy these conditions before expansion:

- All expected nodes receive analysis.
- All graph nodes receive one evolution operation.
- Evidence Recall@5 has no material decrease.
- The final answer has no material quality decrease.
- The result contains no new structured-output failure.

The cold-build target is less than 180 seconds.

## 6. Current system state

- GPU: one NVIDIA L40S with 46,068 MiB available
- GPU state at experiment start: idle
- Embedding server: active on `127.0.0.1:18001`
- VLM server: not active
- Free project storage: approximately 780 GiB

## 7. Sequential observations

### Observation 1

The existing teacher result is sufficient for the first comparison.

Do not repeat the 32B teacher build for `spiqa_58`.

### Observation 2

The previous Qwen2.5-VL-7B failure does not prove that Qwen3-VL-8B cannot do the task.

The previous local server did not enforce structured output. The new test must use grammar-constrained JSON Schema output.

### Observation 3

The official source remains the control. All experimental code and output must stay outside the official source directory.

### Observation 4

The official `Qwen3-VL-8B-Instruct-FP8` checkpoint was installed at
`/mnt/maxtox-nfs-student/zff/models/qwen3-vl-8b-instruct-fp8`.

The first vLLM startup measured:

- Model memory: 10.18 GiB
- KV-cache memory: 29.43 GiB
- KV-cache capacity: 214,288 tokens
- Estimated concurrency at the 24,000-token limit: 8.93 requests

For comparison, the earlier 32B server used 33.48 GiB for model weights and
had capacity for only about 1.03 full-length requests. The 8B checkpoint
therefore creates substantially more room for batching and concurrency.

### Observation 5

The strict structured-output canary completed 14 responses before the server
exited. All 14 completed responses were valid JSON and passed their JSON
Schemas. The responses also preserved the requested numerical value and unit,
and the evolution responses used only valid candidate IDs.

This is a 14/14 structured-output success rate for completed requests. It is
evidence that grammar-constrained decoding solves the earlier malformed-JSON
problem; it is not yet a server-stability pass.

Warm request latency in this small canary was approximately:

- Content-analysis schema: 1.56 seconds
- Evolution schema: 1.20 seconds

### Observation 6

The vLLM EngineCore exited after 14 sequential successful requests. The final
six canary attempts failed with connection errors because the server was no
longer running, not because the model emitted invalid JSON.

The server log contains no CUDA exception, GPU out-of-memory error, Linux OOM
event, or malformed-output error before shutdown. It reports that the process
manager sent SIGTERM to EngineCore, followed by `EngineDeadError`. GPU KV-cache
use was approximately zero at the time. The precise trigger is therefore not
proven by the available log.

This stability failure blocks the full graph build until a safer server launch
passes a repeat canary. No graph-construction time was spent or lost.

### Observation 7

The conservative server configuration passed an extended canary:

- Requests: 40
- Valid JSON: 40/40
- JSON Schema passes: 40/40
- Connection or server errors: 0

The mitigation uses eager execution, reserves 85 percent rather than 95
percent of GPU memory, caps active sequences at eight, and disables sampling
defaults inherited from the model repository. Its measured KV-cache capacity
is 183,056 tokens, or 7.63 requests at the configured 24,000-token maximum.

This passes the structured-output and short-run stability gate. The first full
student graph build may now proceed.

### Observation 8

The first full 8B cold build started in a detached session. It loaded the same
five documents as the teacher and found 130 text chunks. The server is
processing eight simultaneous requests and remains healthy.

### Observation 9

An isolated optimization source tree was created at
`experiments/low_resource_content_graph/implementations/student_8b_behavior_preserving/`.
The control source was not edited during this step.

The first optimization set contains only redundant-work and scheduling
changes:

1. Send embedding inputs in ordered batches of 64.
2. Reuse the stored embedding matrix to compute all evolution neighbours in
   one cosine-similarity operation.
3. Re-embed only nodes whose summary or keywords changed during evolution.
4. Apply the same strict content-analysis JSON Schema on the first request
   instead of only after a malformed response.
5. Allow text and image analysis task queues to overlap while retaining the
   same global VLM concurrency limit.

No node is omitted, no evolution call is omitted, no question-dependent filter
is introduced, and the G2 graph-construction algorithm remains present.

### Observation 10

In the unoptimized 8B build, all 130 text nodes completed successfully. The
text-analysis stage took approximately 6.4 minutes, followed by approximately
1.5 minutes for 130 separate CPU embedding requests.

The visual stage then exposed a severe loose-output tail. Forty-eight of 52
image requests completed, while four requests continued generating for several
minutes under the upstream 8,192-token output allowance. During that tail the
server reported no prompt processing, continuous generation, and no server or
CUDA error. This localizes the delay to unconstrained response generation, not
PDF extraction, disk I/O, or image encoding.

The strict first-attempt schema in the experimental implementation directly
addresses this failure mode by bounding the required fields and preventing
free-form continuation.

### Observation 11

An integration check compared one batched embedding request with three
one-input requests for identical strings. The maximum absolute vector
difference was `1.1920928955078125e-07`, consistent with floating-point batch
noise. Batched requests preserve model choice, input strings, vector order, and
embedding dimensionality.

### Observation 12

The complete unoptimized 8B cold build finished successfully in 1,510.77
seconds (25.18 minutes). It produced 177 nodes and made no server-level errors.

Measured stages:

| Stage | Wall time | Requests | Tokens |
|---|---:|---:|---:|
| Text analysis | 358.97 s | 130 | 226,671 |
| Image analysis | 653.97 s | 55 | 278,819 |
| Text embedding | 76.67 s | 130 | 15,135 |
| Image embedding | 24.09 s | 52 | 4,115 |
| Evolution | 336.05 s | 177 | 1,481,120 |
| Re-embedding | 60.59 s | 177 | 6,940 |

The 55 image-analysis calls represent 52 images plus three retries caused by
8,192-token truncation. The slowest image request took 460.01 seconds.

Total VLM use was 362 calls and 1,986,610 tokens. Total explicit embedding use
was 359 HTTP calls and 26,190 reported tokens. The three principal measured
latency sources are therefore unconstrained visual-output tails, hundreds of
small embedding requests, and the full per-node evolution workload.

### Observation 13

The compiled 8B server passed a concurrent stability test: 40/40 strict-schema
responses were valid at concurrency 20, the slowest request completed in 5.20
seconds, and the server remained healthy.

The first optimized-build launch then stopped before its first model call
because the copied local-runtime adapter inferred the dataset root relative to
the deeper experimental source directory. The failure was a `FileNotFoundError`
for the SPIQA CSV. No graph computation or partial model output was produced.
The adapter was corrected to accept the actual lab root explicitly; this does
not change graph behavior.

### Observation 14

Optimized trial v1 completed in 608.06 seconds (10.13 minutes), a 2.48-fold
speedup over the unoptimized 8B build, but it failed the quality gate.

- Text analysis: 125/130 successful, with five fallback nodes
- Image analysis: 49/52 successful
- Final nodes: 176
- Total VLM calls: 367
- Total VLM tokens: 2,044,384
- Explicit embedding calls: 7, reduced from 359

The real scientific inputs revealed that vLLM's constrained decoder could
still emit a literal tab inside a JSON string. Long keyword/reference lists
also exhausted the 1,536-token limit, and the existing image fallback omitted
three images because it lacked `text_content`. This trial is retained as a
failed optimization result and must not be used for a quality claim.

Batch size 64 was also counterproductive on the six-core CPU embedding path:
text embedding took 168.61 seconds versus 76.67 seconds in the unoptimized run.
The next trial will place the unchanged BGE-M3 model on available GPU headroom
and use smaller batches.

### Observation 15

GPU-hosted BGE-M3 embedded all 177 baseline nodes in 4.28 seconds using batches
of 16. The same stage took 76.67 seconds in the unoptimized CPU run. CPU/GPU
embeddings had minimum per-row cosine agreement above `0.9999999997`.

### Observation 16

Optimized trial v2 reached the raw latency target at 145.71 seconds, but it is
invalid for quality comparison. A zero-length `text_content` constraint caused
111 text summaries to become `No meaningful information`; only 19 text nodes
and 52 visual nodes remained. The result proves the hardware/runtime path can
fit under three minutes, but not yet with an acceptable graph.

The constraint was removed entirely from the text schema because the released
text-analysis prompt does not request `text_content`, and text nodes already
retain the original raw text in `MemoryNote.content`. A targeted rerun of the
ten previously difficult real text chunks produced 10/10 usable summaries and
zero `No meaningful information` summaries.

### Observation 17

Optimized trial v3 completed in 295.28 seconds (4.92 minutes) with 175 nodes.
It is a large improvement but still fails the acceptance gates: two text and
two image analyses required fallbacks, and it exceeds 180 seconds.

- Parallel text/image analysis wall time: approximately 130 seconds
- Evolution wall time: 163.73 seconds
- Evolution prompt and output tokens: 1,396,592
- All embedding and re-embedding work: under five seconds wall time

The next trial keeps one evolution call per node and retains every node's raw
content. For text neighbours inside the evolution prompt, it supplies the
already-generated summary and keywords rather than duplicating each
neighbour's full raw text. Visual nodes and images remain multimodal. This is a
candidate prompt-representation tuning, not yet an accepted equivalence claim;
retrieval and final QA checks must determine whether it is safe.

### Observation 18

Optimized trial v4 completed in 146.77 seconds, below the 180-second latency
target. All 52 images were retained and analyzed, and summary-based text
neighbours reduced evolution from 1.40 million tokens and 163.73 seconds to
521,269 tokens and 56.00 seconds.

However, v4 is rejected for completeness: an overly aggressive bibliography
instruction caused 25 text chunks to be filtered, leaving 157 nodes. That
instruction was removed. The concise keyword/summary bounds, visual recovery,
GPU embeddings, and summary-neighbour evolution remain for the next trial.

### Observation 19

Optimized trial v5 passed the single-example construction gates.

- Cold Content Graph construction: **158.76 seconds (2.65 minutes)**
- Unoptimized 8B construction: 1,510.77 seconds (25.18 minutes)
- Speedup over the same-model control: **9.52x**
- Text analyses: 130/130 usable
- Image analyses: 52/52 usable
- Final graph: 179 nodes (127 text and 52 visual)
- Evolution: 179/179 nodes, one VLM evolution call per retained node
- Structured-output failures that lost a node: 0

Three text requests required a bounded retry and one completed visual response
required deterministic closure of a truncated JSON object. The recovery path
accepted the visual response only after all required keys were present and the
result passed the same JSON Schema. It rejected incomplete text objects in its
targeted tests.

The optimized stage measurements were:

| Stage | Wall time | Requests | Tokens |
|---|---:|---:|---:|
| Text analysis | 60.51 s | 133 | 217,698 |
| Image analysis | 91.64 s | 52 | 240,975 |
| Text embedding | 3.20 s | 9 batches | 8,256 |
| Image embedding | 0.44 s | 4 batches | 3,906 |
| Evolution | 65.41 s | 179 | 606,035 |
| Changed-node re-embedding | 0.92 s | 10 batches | 5,426 |

Text and image queues overlap, so their stage durations must not be added to
infer total wall time. Total VLM use was 364 calls and 1,064,708 tokens.

### Observation 20

Fixed-question retrieval from the v5 graph retained the decisive evidence.
At `k=5`, it retrieved the two ACNN mechanism passages, Figure 1, and the
AdaQA application passage. Its raw-node overlap was 4/5 with the 32B teacher
and 4/5 with the unoptimized 8B graph.

The candidate recovered three of the four teacher text nodes in the saved
teacher trace. The omitted teacher node is general meta-network background;
the replacement is the closely related AdaQA architecture figure. The core
Figure 1 and Section 3.2/3.3 evidence needed for this question was present.

The complete comparison, including node hashes, summaries, raw previews, and
cosine scores, is saved in `results/retrieval_comparison_v5.json`.

### Observation 21

The official G2 Planning Graph, Worker, sufficiency checker, and final
synthesis pipeline was run without rebuilding either graph.

| Graph | Cached query time | Final-answer assessment |
|---|---:|---|
| 32B teacher | about 217 s after construction | Correct mechanism; omits joint differentiability/end-to-end training |
| Unoptimized 8B | 32.62 s | Correct mechanism; omits joint differentiability/end-to-end training |
| Optimized v5 | 37.85 s | Correct mechanism; omits joint differentiability/end-to-end training |

The v5 answer says that the generation module encodes the input, creates
input-conditioned filters through deconvolution, and that the convolution
module applies those sample-specific filters to adapt feature extraction for
each sentence. This matches the same substantive mechanism recovered by both
controls. All three answers omit the same extra reference detail that the two
modules are jointly differentiable and trainable end to end.

Therefore, v5 shows **no material retrieval or final-answer decrease on this
one controlled example**. This is not yet a dataset-level no-regression claim.

### Observation 22

The successful v5 optimization does not introduce question-dependent node
filtering or selective evolution. It retains G2's basic construction path:

1. Analyze every extracted text chunk and visual.
2. Embed the resulting summaries and keywords.
3. Initialize graph links.
4. Run one VLM evolution operation for every retained node.
5. Re-embed summaries changed by evolution.
6. Save the graph for query-independent reuse.

The speedup comes from constrained concise outputs, concurrent request
scheduling, GPU batched embeddings, matrix-based neighbour selection,
changed-node-only re-embedding, and using existing neighbour summaries rather
than copying full raw neighbour text into evolution prompts. Raw node evidence
remains stored and is returned at retrieval time.

### Observation 23

The first expansion attempt on `spiqa_108` localized two small-model failure
modes that were not visible in `spiqa_58`:

1. An individual keyword string could repeat until the 1,024-token text limit,
   even though the array itself was limited to 12 items.
2. Valid bibliography/equation chunks could be labeled `No meaningful
   information` and then deleted by the upstream sentinel filter.

That first attempt finished in 134.68 seconds but retained only 163 of the
teacher's 169 nodes and had one failed text analysis. It was rejected.

The repair constrains each keyword and tag string length in the JSON Schema,
uses modality-correct retry fields, and preserves a raw evidence node with a
bounded extractive metadata fallback when analysis fails or returns a false
`No meaningful information` sentinel. This fallback is query-independent and
does not change the raw evidence stored in `MemoryNote.content`.

The repeated `spiqa_108` build then analyzed 106/106 text chunks and 63/63
images, retained all 169 nodes, and remained below the latency target.

### Observation 24

The first `spiqa_378` numerical-table build exposed a retrieval-quality
regression even though construction was complete and fast:

- Construction: 109.33 seconds
- Nodes: 165/165 extracted nodes retained
- Semantic top five: related Table 3 ranked before decisive Table 4
- Final answer: incorrect values from Table 3

The initial, pre-evolution student graph ranked the correct Table 4 first.
After evolution, the 8B model's shorter rewritten summary moved Table 4 to
rank four. Because official G2 expands the first semantic seed through graph
links before considering later seeds, Table 4 did not enter the returned five.
This localized the regression to destructive information loss in evolved
retrieval metadata, not missing OCR, node deletion, or the Worker.

### Observation 25

A query-independent representation repair retains both views when a node is
updated:

```text
retrieval embedding = embed(initial analysis + evolved analysis)
```

The evolved summary remains the node's active G2 context, all evolved links
remain active, and every node still receives its official evolution call. The
initial analysis is retained only in the retrieval vector so evolution cannot
erase a discriminative table title, metric, value, or entity.

On the repeated `spiqa_378` build, this restored Table 4 to semantic rank one,
raised raw-node overlap with the teacher to 4/5, and recovered all three
teacher text evidence nodes represented in its saved trace. The official G2
answer then exactly matched the reference:

- Method: DLA
- nDCG@10: 0.421
- ERR@10: 0.582
- Improvements over NoCorrect: 0.063 and 0.082

Construction took 106.81 seconds and cached inference took 34.95 seconds.

### Observation 26

Final cold builds using one consistent implementation produced:

| Question | Evidence type | Nodes | Construction | Teacher overlap@5 | QA result |
|---|---|---:|---:|---:|---|
| `spiqa_58` | Figure + explanatory text | 182 | 156.47 s | 4/5 | Correct mechanism; same omitted detail as controls |
| `spiqa_108` | Multi-line chart | 169 | 134.75 s | 3/5 | Correct raw synthesis; official tag parser returned `None` |
| `spiqa_378` | Numerical table | 165 | 106.81 s | 4/5 | Exact reference answer |

Mean cold construction time was **132.68 seconds (2.21 minutes)**. Maximum
construction time was **156.47 seconds (2.61 minutes)**. All three complete
graphs were under 180 seconds, retained every extracted text and visual node,
and ran one evolution call per node.

### Observation 27

`spiqa_108` separates Content Graph quality from an existing online
orchestration/parser failure. The final graph retrieves Figure 3 and supporting
ESMM result text. The raw final synthesis states the correct reference result:
ESMM-NS and ESMM consistently outperform all other models across all sampling
rates for both CVR and CTCVR, with ESMM generally higher.

However, the official sufficiency checker unnecessarily demanded exact chart
values not required by the benchmark answer, exhausted four adjustment rounds,
and the final model output omitted the closing `</output>` tag. The unchanged
official `extract_output()` therefore returned `None`. An earlier run on the
same evidence type parsed successfully in 55.37 seconds and gave the correct
conclusion. The failed final parse is retained as evidence and is not counted
as a clean operational QA pass.

This means the three-example result supports the Content Graph latency and
evidence-preservation claim, but it also confirms that official G2's online
sufficiency/refinement and tag parsing still need a separate reliability
audit. No such online repair was added to this construction experiment.

## 8. Live status

Status: **the three-example Content Graph experiment is complete.** All three
final cold builds are below 180 seconds, all extracted nodes are retained, and
the decisive evidence is retrieved for the mechanism, chart, and table cases.

Next action: treat this as a successful small pilot, not a dataset-level proof.
Before a production claim, run a larger fixed evaluation set and separately
repair/test the official online sufficiency and output-parsing failures exposed
by `spiqa_108`.

## 9. Follow-up teacher/student loss evaluation

A fixed five-question comparison was subsequently completed using all saved
32B teacher graphs. The same seeded 8B online reader was run on both teacher and
candidate graphs to isolate graph-construction loss.

The optimized builder retained decisive top-5 evidence on all five questions
and averaged 141.14 seconds, but it did not pass the no-regression gate:

- teacher-graph matched-reader correctness: 5/5;
- candidate-graph parsed correctness: 3/5;
- candidate raw semantic correctness: 4/5;
- one confirmed substantive loss on `spiqa_540` despite the correct figure
  being retrieved at rank one;
- mean candidate-graph query latency was 2.40 times the teacher-graph latency
  because of additional sufficiency refinement.

The complete protocol, traces, failure attribution, and machine-readable
results are in `loss_evaluation/REPORT.md` and `loss_evaluation/RESULTS.json`.

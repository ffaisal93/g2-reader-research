# Loss Evaluation: Official-Style 32B Teacher vs Optimized 8B Content Graph

## Executive result

The optimized 8B builder is genuinely much faster, but the five-question
matched pilot identifies a measurable quality/reliability loss.

- Mean teacher construction: **2,979.94 seconds (49.67 minutes)**
- Mean optimized construction: **141.14 seconds (2.35 minutes)**
- Mean construction speedup: **21.11x**
- Maximum optimized construction time: **169.10 seconds**
- Candidate decisive evidence present in top 5: **5/5**
- Raw candidate/teacher node overlap@5: **16/25 (64%)**
- Same 8B reader on teacher graphs: **5/5 correct**
- Same 8B reader on candidate graphs: **3/5 parsed correct**
- Candidate raw semantic correctness, ignoring one parser failure: **4/5**
- Mean query time on teacher graphs: **47.27 seconds**
- Mean query time on candidate graphs: **113.57 seconds**

The main loss is not simple retrieval recall. The candidate retrieved the
decisive evidence for every question. The observed failures arise because the
8B-generated graph metadata presents visual/table evidence less reliably to
the Worker and sufficiency checker.

This is a fixed five-question pilot, not a dataset-level accuracy estimate.

## Experimental design

The protocol was written before the new runs and is saved in
`EVALUATION_PROTOCOL.md`.

The fixed set contains every question for which the expensive saved 32B graph
was available:

1. `spiqa_58` — figure plus explanatory text;
2. `spiqa_108` — multi-line chart;
3. `spiqa_378` — numerical table;
4. `spiqa_540` — figure/formula comparison;
5. `spiqa_542` — numerical table/figure lookup.

To isolate Content Graph construction quality, both graph variants were read
by the same seeded `Qwen3-VL-8B-Instruct-FP8` Planning Graph, Worker,
sufficiency, and final-synthesis pipeline. The only paired-run difference was
the saved Content Graph directory.

The original traced source remained frozen. New candidate graphs, QA outputs,
retrieval comparisons, and reports were written only under the experiment
directory.

## Construction results

| Question | Teacher nodes | Candidate nodes | Teacher build | Candidate build | Speedup |
|---|---:|---:|---:|---:|---:|
| `spiqa_58` | 182 | 182 | 3,227.84 s | 156.47 s | 20.63x |
| `spiqa_108` | 169 | 169 | 2,392.51 s | 134.75 s | 17.76x |
| `spiqa_378` | 164 | 165 | approximately 2,347 s | 106.81 s | 21.97x |
| `spiqa_540` | 199 | 203 | 4,226.00 s | 169.10 s | 24.99x |
| `spiqa_542` | 179 | 179 | 2,706.37 s | 138.55 s | 19.53x |

The teacher removed some chunks after the model emitted the upstream
`No meaningful information` sentinel. The candidate preserves every extracted
raw evidence node, explaining the small node-count increases for `spiqa_378`
and `spiqa_540`.

Four teacher times are sums of the instrumented official construction-stage
durations. `spiqa_378` is an elapsed timestamp estimate because its original
online run lost the model server after saving the graph but before writing its
usage summary. Candidate times are direct wall-clock measurements around
`construct_memory()`. Neither side includes MinerU PDF parsing or model-server
startup.

Across the five candidate builds:

- VLM calls: **1,796**
- VLM tokens: **5,092,334**
- explicit embedding HTTP calls: **109**
- mean nodes: **179.6**
- all extracted text and visual nodes retained;
- one evolution call executed for every node;
- no question-dependent filtering or selective evolution.

## Retrieval results

| Question | Candidate/teacher overlap@5 | Traced teacher text hits | Decisive evidence in candidate top 5 |
|---|---:|---:|---|
| `spiqa_58` | 4/5 | 3/4 | Yes |
| `spiqa_108` | 3/5 | 1/3 | Yes |
| `spiqa_378` | 4/5 | 3/3 | Yes |
| `spiqa_540` | 2/5 | 0/3 | Yes, Figure 3 ranked first |
| `spiqa_542` | 3/5 | 2/4 | Yes, decisive table ranked first |

Raw overlap is only diagnostic. Different nodes may carry equivalent evidence.
The important result is that candidate top-5 retrieval contained the decisive
figure/table/passage for all five questions. Therefore, the observed answer
loss cannot be described as conventional `retrieval_failure`.

## Matched online-reader results

| Question | 8B reader on teacher graph | Time | 8B reader on candidate graph | Time | Assessment |
|---|---|---:|---|---:|---|
| `spiqa_58` | Correct | 36.79 s | Correct | 40.94 s | No material loss |
| `spiqa_108` | Correct and parsed | 110.13 s | Correct raw answer, parsed `null` | 253.51 s | Sufficiency + parser failure |
| `spiqa_378` | Exact answer | 40.30 s | Exact answer after repair | 155.52 s | Worker misread repaired by refinement |
| `spiqa_540` | `DMRNet` | 28.04 s | `Not available...` | 31.87 s | Confirmed accuracy loss |
| `spiqa_542` | `RCE` | 21.08 s | `RCE` | 86.02 s | Correct, unnecessary refinement |

### Saved original 32B full-pipeline outputs

The earlier original-style runs used the 32B model for construction and online
reasoning. Four completed predictions are available and all four are
semantically correct: `spiqa_58`, `spiqa_108`, `spiqa_540`, and `spiqa_542`.
The original `spiqa_378` online attempt cannot be scored because its local
model server exited after graph construction and repeated connection failures
prevented Planning Graph generation.

That saved full-pipeline comparison mixes graph-builder and answer-model
effects, so it is secondary evidence. The matched same-reader results above are
the stronger test of Content Graph loss.

### `spiqa_58`: no observed loss

Both graphs led the same reader to the correct substantive mechanism: the
generation module creates input-conditioned filters and the convolution module
uses them to encode each sentence adaptively. Both omit the reference's extra
joint-differentiability/end-to-end-training detail.

### `spiqa_108`: evidence is present, orchestration becomes less stable

Both graphs contain Figure 3 and the supporting ESMM text. On the teacher graph,
the shared reader stopped after one refinement and returned the correct parsed
conclusion in 110.13 seconds.

On the candidate graph, the sufficiency checker demanded unnecessary exact
chart values, exhausted all four rounds, and took 253.51 seconds. Final
synthesis stated the correct benchmark conclusion, but omitted the closing
`</output>` tag, so the official parser returned `null`.

This is not missing evidence. It is an interaction between candidate evidence
presentation, the official sufficiency loop, and brittle output parsing.

### `spiqa_378`: correct answer, but Worker-support instability

The candidate retrieved the decisive Table 4 at semantic rank one. One Worker
correctly read DLA as `0.421/0.582`; another initially misread the NoCorrect row
as having the same values and computed zero improvement. Global refinement
eventually recovered the exact reference answer:

- DLA;
- nDCG@10 `0.421`;
- ERR@10 `0.582`;
- improvements `0.063` and `0.082`.

The answer is correct, but query latency rose from 40.30 to 155.52 seconds.
This is a repaired `worker_support_failure`, not a clean no-loss result.

### `spiqa_540`: confirmed accuracy loss

This is the clearest loss attributable to using the smaller graph builder.

The candidate retrieved the correct Figure 3 at rank one. Its stored OCR/text
explicitly says:

```text
Left: L = 9. Right: L = 24.
ResNet: 20.0 +/- 4.24
DILNet: 14.0 +/- 2.83
DMRNet: 8.0 +/- 2.83
```

Nevertheless, the Worker interpreted the panels as `L=12` and `L=96`, claimed
that no `L=9` figure was available, and returned `Not available in the provided
materials.` The teacher graph's richer visual summary allowed the identical
reader to answer `DMRNet`.

Therefore, preserving the raw image and retrieving it at rank one is not
sufficient. The quality of the graph's visual analysis/context can materially
change downstream multimodal reasoning.

### `spiqa_542`: correct but slower

Both graphs led to `RCE`. The candidate graph nevertheless caused an
unnecessary adjustment round, increasing latency from 21.08 to 86.02 seconds.

## What loss is actually caused by the 8B construction model?

The pilot supports four conclusions.

1. **Node preservation is strong.** Every extracted raw node was retained.
2. **Top-5 decisive-evidence recall is strong on this set.** It was 5/5.
3. **Visual/table metadata quality is less reliable.** `spiqa_540` fails even
   though the correct evidence ranks first; `spiqa_378` initially misreads a
   table row.
4. **The candidate graph makes the official sufficiency checker less stable.**
   Three questions (`108`, `378`, `542`) needed substantially more refinement
   than their teacher-graph counterparts.

The safe engineering optimizations—batched embeddings, matrix neighbor search,
GPU embedding, concurrent request scheduling, and changed-node-only
re-embedding—do not themselves remove evidence. The risk comes primarily from
replacing the 32B graph-analysis/evolution model with 8B and compressing its
visual/evolution descriptions.

Retaining initial plus evolved analysis in the retrieval embedding repaired the
previous `spiqa_378` retrieval regression, but it does not guarantee that the
downstream Worker will correctly interpret every retrieved visual.

## Defensible conclusion

The current optimized implementation provides approximately **21x faster
Content Graph construction**, bringing five cold graph builds below three
minutes. It does **not** yet preserve the teacher's operational quality.

On this five-question matched pilot:

- parsed accuracy changed from **5/5 to 3/5**;
- raw semantic accuracy changed from **5/5 to 4/5**;
- one question had a confirmed substantive answer loss;
- two additional correct questions required expensive refinement;
- mean cached-query time became **2.40x slower** on candidate graphs.

Because the sample is small, the numerical rates must not be presented as
dataset accuracy. But the observed failure is sufficient to reject a claim of
"no performance loss."

## Recommended next experiment

Before expanding to 100 questions, localize the teacher/student difference on
the five decisive visual nodes:

1. compare 32B and 8B initial visual analyses field by field;
2. compare their evolved summaries and links;
3. replay the same Worker prompt with raw image plus teacher summary and raw
   image plus student summary;
4. determine whether teacher-quality visual summaries alone repair `spiqa_540`
   and remove extra refinements for `108`, `378`, and `542`;
5. only then evaluate a narrowly scoped teacher fallback or distilled visual
   analyzer.

This keeps the G2 research path intact and identifies the minimum teacher
capability needed instead of hiding the loss with a question-specific rule.

## Artifacts

- `EVALUATION_PROTOCOL.md` — predeclared design and interpretation
- `RESULTS.json` — machine-readable consolidated results
- `retrieval/*.json` — node-level teacher/candidate comparisons
- `matched_qa/teacher_graph/` — same-reader teacher-graph outputs and traces
- `matched_qa/candidate_graph/` — same-reader candidate-graph outputs and traces
- `candidate_builds/` — new `spiqa_540` and `spiqa_542` graph builds
- `prepare_results.py` — reproducible result consolidation
- `run_matched_qa.sh` — reproducible matched-query runner

## Follow-on 100-question audit

The larger failure audit is now running from
`experiments/failure_audit_100/`. It uses per-question atomic checkpoints,
append-only journaling, service health checks, bounded retries, and separate
build/query states, so an interrupted process can resume without rebuilding
validated graphs or overwriting completed traces. Its live findings are in
`experiments/failure_audit_100/REPORT.md` and machine-readable progress is in
`experiments/failure_audit_100/PROGRESS.json`.

This follow-on run remains explicitly labeled as the optimized-8B
low-resource configuration. Candidate-model/parser confounds will be separated
from failures that can be validated against the original 32B G2 path.

# Consolidated G²-Reader Experimental Findings

Last updated: 2026-08-26

This is the single, authoritative narrative of the G²-Reader experiments in
this workspace. It combines the official-runtime audit, the low-resource
Content Graph experiment, the teacher/student loss evaluation, the resumable
SPIQA-100 failure audit, matched 32B replays, parser recovery, and raw-image
adjudication.

The detailed reports and immutable traces remain the evidence base. When an
early automated classification conflicts with the later raw-source review, the
raw-source decision recorded here takes precedence.

## 1. Executive conclusion

The experiments establish five main results.

1. **Official-style G² Content Graph construction is computationally
   expensive in this environment.** Across five saved 32B teacher graphs, mean
   construction time was 2,979.94 seconds, or 49.67 minutes, for a bundle of
   roughly 165–199 nodes. The pipeline performs one initial VLM analysis per
   node and one VLM evolution call per node, producing hundreds of multimodal
   calls and roughly two million tokens per graph.

2. **A low-resource implementation can reduce cold construction to about
   2–3 minutes without removing the G² construction stages.** The optimized 8B
   builder averaged 141.14 seconds across five graphs, a 21.11× construction
   speedup. It retained all extracted evidence nodes and still evolved every
   node once. This is a real throughput improvement, not a result of
   question-dependent filtering or selective evolution.

3. **The fast builder does not yet preserve teacher operational quality.** In
   the five-question matched comparison, the same 8B online reader answered
   5/5 correctly on 32B teacher graphs, but only 3/5 were officially parsed as
   correct on optimized-8B graphs. Ignoring one final-tag parser loss, raw
   semantic correctness was 4/5. The candidate retrieved decisive evidence in
   all five cases, so the loss is primarily evidence-description and
   Worker/checker interaction, not ordinary top-5 retrieval recall.

4. **The 100-question audit identifies Worker evidence use as the dominant
   answer-stage weakness.** After excluding five defective benchmark cases,
   the optimized-8B configuration produced 65/95 semantically correct parsed
   or recoverable raw answers and 30 incorrect/no-answer outcomes. Corrected
   failure phenomena were: Worker support 20, parser 9, retrieval 4,
   decomposition 2, and composition 1.

5. **Some failures belong to the released G² integration, not just the small
   model.** The official online path relies on prompt-generated tagged JSON
   without schema enforcement. A matched 32B replay reproduced the malformed
   Planning Graph for `spiqa_96` on all 15 retries. The final answer parser also
   discards otherwise correct answers when `</output>` is missing. These are
   system-interface defects even though model choice affects how often they
   occur.

The defensible overall conclusion is:

> We have a substantially faster G²-compatible Content Graph builder and a
> source-grounded map of the remaining failures, but we do not yet have a
> no-regression replacement for the 32B teacher or a production-reliable G²
> online reader.

## 2. What system was evaluated

G² has two distinct phases that must not be conflated.

### 2.1 Offline Content Graph construction

```text
processed documents
  → ordered text, table, and figure nodes
  → per-node VLM analysis
  → embeddings and initial links
  → per-node graph evolution
  → changed summaries re-embedded
  → saved Content Graph
```

This phase is conceptually query-independent. Once a graph for a fixed
document collection exists, questions should reuse it.

### 2.2 Online question answering

```text
question
  → Content Graph retrieval
  → Planning Graph decomposition
  → dependency-ordered Workers
  → sufficiency check
  → optional global refinement/replanning
  → final synthesis
  → <output> tag parser
```

The Content Graph affects what evidence is retrieved and how that evidence is
described. The Planning Graph controls which reasoning tasks execute and how
their answers depend on one another. The final parser determines whether the
generated answer becomes an official prediction.

### 2.3 Compared configurations

The experiments used three related but non-equivalent configurations:

- **32B teacher construction:** official traced construction with
  `Qwen3-VL-32B-Instruct-FP8`.
- **Optimized 8B construction:** a behavior-preserving scheduling and
  redundancy optimization using `Qwen3-VL-8B-Instruct-FP8`, concise structured
  outputs, and the same basic G² graph stages.
- **Matched online reader replays:** the graph was held fixed while the online
  reader was changed, or the reader was held fixed while teacher and candidate
  graphs were compared.

The 100-question accuracy and failure counts describe the **optimized-8B graph
plus official G² online path**. They must not be presented as the accuracy of
the original end-to-end 32B G² system.

## 3. Experiment sequence and why it matters

The findings were obtained sequentially:

1. Audit and minimally repair released runtime blockers so official G² could
   execute locally without changing its reasoning algorithm.
2. Measure an expensive fixed-seed 32B teacher graph.
3. Validate whether strict structured decoding makes an 8B VLM usable.
4. Optimize one graph first, then expand only after it passed completeness and
   latency gates.
5. Compare five saved teacher graphs with five optimized graphs under the same
   online reader.
6. Run a resumable 100-question SPIQA audit with complete passive traces.
7. Recover explicit raw answers rejected by the official parser.
8. Semantically adjudicate suspected errors and classify their earliest causal
   failure.
9. Replay selected cases with the 32B reader while holding the Content Graph
   fixed.
10. Inspect 12 disputed table/figure cases against the exact raw images and
    correct the final labels.

This ordering prevents three common mistakes: treating lexical mismatch as an
error, attributing an 8B model failure to G² itself, and calling a benchmark
reference defect a system failure.

## 4. Failure taxonomy

The categories identify the **earliest decisive point** at which the system
lost the ability to produce a supported answer. Later downstream errors may be
recorded as secondary phenomena.

### 4.1 `dataset_failure`

Definition: the benchmark question, reference answer, or question/reference
pair is malformed or contradicted by the source. The system cannot be fairly
scored against that row.

Diagnostic test:

- Read the literal question and reference.
- Inspect the original paper text, table, or figure.
- Ask whether a source-supported answer can satisfy both the question and the
  reference.

Example — `spiqa_452`:

- The figure says bubble size represents tOF.
- ENet is visibly the largest bubble.
- Lower tOF indicates better temporal coherence.
- The question equates the largest/highest tOF with the best result, while the
  reference answers TecoGAN, which has better low tOF.

This is not a G² error: the question itself combines incompatible criteria.

Other excluded cases:

- `spiqa_79`: the stored question is only `New question:`.
- `spiqa_164`: the reference answers the overall five-hop topology, while the
  literal question asks about directly connected Node 1.
- `spiqa_195`: the reference says both ACGAN losses fall, contradicting the raw
  curves.
- `spiqa_281`: the reference claims a globally inverse frequency relationship,
  while the source describes a hump-shaped Luhn profile.

Final count: **5 excluded benchmark cases**.

### 4.2 `retrieval_failure`

Definition: the information required to answer the question is absent from the
evidence delivered to the relevant Worker. Retrieving a related table or an
OCR fragment is not sufficient if the decisive row, column, figure, or passage
is missing.

Diagnostic test:

- Identify the minimum source evidence needed for the answer.
- Inspect the actual retrieved node IDs and payloads.
- If the evidence is not present, changing Worker reasoning alone cannot fix
  the case.

Example — `spiqa_578`:

- The question asks for the **topic words** having the highest internal
  coherence.
- Retrieval returned Table 4, which reports model-level NPMI and makes SCHOLAR
  look best.
- The required Table 6 topic row was not retrieved.
- The missing answer was `turks armenian armenia turkish roads escape soviet
  muslim mountain soul`, with coherence 0.77.

The Worker answered `SCHOLAR`, but the earliest decisive problem was that the
topic table was unavailable. Raw-image review therefore corrected this from a
provisional Worker label to retrieval failure.

Final count: **4** — `spiqa_292`, `spiqa_396`, `spiqa_510`, and `spiqa_578`.

### 4.3 `worker_support_failure`

Definition: the decisive evidence was retrieved, but a Worker misread it,
selected the wrong row/panel/entity, performed an unsupported inference, or
claimed that visible evidence was unavailable.

Diagnostic test:

- Verify that the exact evidence was in the Worker's context.
- Compare every extracted value, label, unit, and claim with that evidence.
- If the plan was adequate but the intermediate answer is unsupported, the
  failure is at the Worker.

Example — `spiqa_4`:

- The retrieved table gives 16,198 total negative CNSE samples.
- The question asks for the number allocated to a 60% training split.
- The Worker copied 16,198 instead of computing approximately 9,719.

Example — `spiqa_116`:

- The correct figure was retrieved.
- At x=7, the proposed and Yosinski multi-shot curves are both around 71–72%,
  with only a marginal difference.
- The 8B answer invented an approximately ten-point advantage; even the 32B
  replay's exact 75-versus-70 values came from incorrect x positions.

Example — `spiqa_368`:

- The correct MNIST attack curves were retrieved and readable.
- Workers repeatedly said the required attack evidence was unavailable.
- The final generation then ended without a usable answer tag.

This was initially suspected to be retrieval failure. Raw visual inspection
showed that retrieval succeeded, so Worker support is primary and parser loss
is secondary.

Final count: **20**, the largest category. Eighteen of the twenty rationales
contain table, figure, value, or trend language.

### 4.4 `decomposition_failure`

Definition: the Planning Graph omits, distorts, or incorrectly frames a
subproblem required by the question. Even competent Workers cannot reliably
recover an operation that the plan never asks them to perform.

Diagnostic test:

- Break the question into the minimum evidence and reasoning operations.
- Compare that set with the generated Planning Graph nodes and dependencies.
- Check especially for missing comparisons, complements, aggregations,
  conditions, or entity disambiguation.

Example — `spiqa_44`:

- The question asks for differences between sickle-cell and leukemia temporal
  patterns.
- The plan creates separate tasks for each patient.
- It never creates the required comparison task.
- The final answer focuses on leukemia and does not answer the comparative
  question.

Example — `spiqa_571`:

- The plan insists on finding a single step whose input/output is directly
  5,119→1,955.
- The table shows a multi-step reduction and Step 4 produces the final 1,955.
- The incorrect framing prevents the system from accepting Step 4 and it emits
  no answer.

Final count: **2** — `spiqa_44` and `spiqa_571`.

### 4.5 `composition_failure`

Definition: retrieval and intermediate Worker answers are adequate, but a
parent task or final synthesis combines them incorrectly.

Diagnostic test:

- Verify the supporting intermediate values independently.
- Recompute the requested comparison from those values.
- If the inputs are correct and the final transformation is wrong, it is a
  composition failure rather than a retrieval or Worker extraction failure.

Example — `spiqa_47`:

- Workers correctly recover disagreement rates of 44.85% before intervention,
  24.92% after GBI, and 33.91% after A*.
- The individual reductions, 19.93 and 10.94 percentage points, are correct.
- Final synthesis reports their 8.99-point absolute difference rather than the
  comparison intended by the reference.

Final count: **1**.

### 4.6 `sufficiency_failure`

Definition: the sufficiency checker makes the wrong control decision. It may
stop while a specific evidence gap remains, or demand unnecessary detail and
trigger expensive global refinement even though the benchmark question is
already answerable.

This category can be an accuracy failure or only an efficiency failure. It is
not a final primary category in the corrected 30 incorrect/no-answer outcomes,
but it appears repeatedly as a secondary operational problem.

Example — `spiqa_542`:

- The first Worker had the decisive `RCE = 0.77` row.
- A sufficiency response was truncated and could not be parsed.
- Official G² treated the parse failure as `insufficient`.
- It ran four Planning Graph executions, 13 Worker tasks, four checks, and 22
  online model calls before returning the already available correct answer.

Example — `spiqa_108`:

- Figure 3 and supporting ESMM text were present.
- The checker demanded exact chart values not required by the question.
- Candidate-graph inference exhausted four adjustment rounds, took 253.51
  seconds, and then lost a correct raw answer to the final tag parser.

The current global refinement policy can therefore turn a small checker or
formatting error into several minutes of redundant work.

### 4.7 `parser_failure`

Definition: the model generated enough correct reasoning or answer content,
but a machine-readable interface rejected it. Two distinct parser locations
must be distinguished.

#### Planning Graph parser failure

The online planner emits JSON inside `<dag>` tags, but the released call does
not require a JSON schema. Malformed JSON prevents Worker execution.

Example — `spiqa_96`:

- The graph was built correctly.
- Every Planning Graph attempt contained invalid JSON escapes such as a single
  LaTeX backslash inside a JSON string.
- The matched 32B reader reproduced this across all 15 official retries.

This proves an official-path structured-output integration defect; it is not
only an 8B incapability.

#### Final-output parser failure

The official parser expects a complete `<output>...</output>` pair. If the
answer is correct but the closing tag is missing, the official prediction is
`null`.

Example — `spiqa_39`:

- The raw answer correctly says TRPO aligns with the true gradient more quickly
  than PPO.
- The opening `<output>` tag is present but `</output>` is missing.
- Derived recovery can identify the answer, but the frozen official parser
  returns no prediction.

Across 98 completed query outputs, 80 parsed officially, ten explicit unclosed
outputs were recoverable, and eight had no safe candidate answer. After
semantic review, six **correct** raw answers among valid cases were confirmed
lost solely by final parsing.

Final corrected parser-phenomenon count: **9**. This includes parser failures
that caused incorrect/no-answer outcomes and correct raw answers lost by the
official interface.

### 4.8 `infrastructure_failure`

Definition: execution fails because of code plumbing, service health, missing
clients, incompatible function signatures, filesystem paths, GPU/server
termination, or artifact-writing problems—not because the reasoning pipeline
answered incorrectly.

Examples found while enabling the official runtime:

- `embed_aclient` was undefined, causing all embeddings to fail.
- `_call_llm_evolve()` was called with `max_tokens` although its released
  signature did not accept that argument; per-node exception handling then
  silently skipped evolution.
- Saved graph directories used `<id>_iter_<round>`, while the cache existence
  check looked only for `<id>`, preventing graph reuse.
- Final logging accessed `item['judge']` even when the optional field was
  absent, crashing after successful synthesis.
- One 8B vLLM process exited after 14 successful canary requests; the logs show
  SIGTERM but no CUDA, GPU-memory, or malformed-output cause.

Infrastructure-blocked runs are excluded from QA accuracy denominators.

### 4.9 `unverifiable`

Definition: the available stored evidence is too coarse, clipped, unreadable,
or provenance-ambiguous to determine whether the system or benchmark is
correct.

This is a temporary audit status, not proof of failure. The 12 disputed visual
cases were resolved by decoding exact graph images and matching them to source
images using dimensions and perceptual hashes. Therefore, **zero** cases remain
unverifiable after raw-image review.

### 4.10 `no_failure`

Definition: the answer is semantically correct and sufficiently supported,
even if it is not a lexical match to the benchmark reference or contains minor
nonmaterial imprecision.

Example — `spiqa_163`:

- The answer describes recursive four-way subdivision and reuse of the Hilbert
  pattern.
- This substantially matches the vague reference.
- Raw visual review restored it from a provisional failure to `no_failure`.

This category matters because strict exact matching was extremely misleading:
the live dashboard showed only five normalized exact matches, while final
semantic/source adjudication found 65 correct answers among 95 valid cases.

## 5. Corrected SPIQA-100 outcome accounting

### 5.1 Denominator

- Requested questions: **100**
- Invalid benchmark cases: **5**
- Valid questions: **95**

The excluded IDs are `spiqa_79`, `spiqa_164`, `spiqa_195`, `spiqa_281`, and
`spiqa_452`.

### 5.2 Correctness

- Officially parsed and semantically correct: **59/95**
- Additional correct raw answers rejected by the parser: **6**
- Total semantically correct parsed/recoverable answers: **65/95**
- Incorrect or no-answer outcomes: **30/95**
- Remaining ambiguous valid outcomes: **0**

### 5.3 Failure phenomena

| Failure phenomenon | Count | Interpretation |
|---|---:|---|
| Worker support | 20 | Retrieved evidence was misread or unsupported claims were produced. |
| Parser | 9 | Planning/final structured output could not be consumed. |
| Retrieval | 4 | Decisive evidence was not delivered to the task. |
| Decomposition | 2 | The plan omitted or distorted a required operation. |
| Composition | 1 | Correct intermediate results were combined incorrectly. |
| **Total phenomena** | **36** | 30 wrong/no-answer outcomes plus six correct raw answers lost by parsing. |

The table counts failure phenomena, not 36 distinct wrong questions. A case may
have a primary cause and a secondary parser or checker consequence.

## 6. Content Graph construction findings

### 6.1 Why the original-style build was slow

For `spiqa_58`, the 32B teacher processed five documents and 182 nodes:

- 130 text-analysis calls;
- 53 image-analysis calls, including one retry;
- 182 evolution calls;
- 365 total VLM calls;
- 2,263,224 VLM tokens;
- 45,916 explicit embedding tokens.

Measured stage time was dominated by VLM work, especially evolution and visual
analysis. Graph bookkeeping and disk operations were not the main bottleneck.
More HDD capacity would help retain caches and artifacts, but it would not make
hundreds of GPU inference calls substantially faster.

The unoptimized 8B build still took 1,510.77 seconds (25.18 minutes). Its three
largest avoidable costs were:

- unconstrained visual responses running to an 8,192-token limit;
- hundreds of one-item embedding HTTP requests;
- large raw-neighbor payloads repeated in every evolution prompt.

### 6.2 Optimizations that produced the speedup

The successful implementation used:

- strict, bounded JSON schemas on the first analysis attempt;
- concurrent text and image analysis under a global request limit;
- batched BGE-M3 embeddings on available GPU headroom;
- matrix-based neighbor selection from the existing embedding matrix;
- re-embedding only summaries/keywords changed by evolution;
- concise initial-plus-evolved retrieval representations;
- existing neighbor summaries rather than duplicating full raw text in every
  evolution prompt;
- bounded recovery that retains raw evidence nodes when analysis metadata
  fails.

It did **not** introduce question-conditioned filtering, skip nodes, or remove
per-node evolution.

### 6.3 Performance achieved

Across the final five-graph comparison:

| Metric | 32B teacher | Optimized 8B candidate |
|---|---:|---:|
| Mean construction time | 2,979.94 s | 141.14 s |
| Mean construction time | 49.67 min | 2.35 min |
| Mean speedup | — | 21.11× |
| Maximum candidate time | — | 169.10 s |

In the 100-question run:

- all 100 Content Graphs completed;
- mean new graph time was 160.85 seconds;
- 98 queries completed and two exhausted Planning Graph serialization retries;
- mean completed online-query time was 71.82 seconds.

### 6.4 Failed optimization trials were informative

Sub-three-minute time alone was not accepted as success:

- Trial v1 lost analyses because bounded structured outputs still allowed edge
  cases such as literal tabs and truncated lists.
- Trial v2 finished in 145.71 seconds but deleted most useful text nodes due to
  a zero-length `text_content` schema mistake.
- Trial v4 finished in 146.77 seconds but an aggressive bibliography rule
  removed 25 valid chunks.

These runs demonstrate why node completeness and retrieval/QA checks must
accompany latency measurements.

## 7. Quality loss from the fast Content Graph

The five-question paired test held the online 8B reader fixed and changed only
the graph.

| Metric | Teacher graph | Candidate graph |
|---|---:|---:|
| Decisive evidence in candidate top 5 | — | 5/5 |
| Parsed correct answers | 5/5 | 3/5 |
| Raw semantically correct answers | 5/5 | 4/5 |
| Mean cached-query time | 47.27 s | 113.57 s |

Candidate graph query time was therefore 2.40× slower even though construction
was far faster. The online checker invoked more refinement on candidate graph
metadata.

### 7.1 The clearest quality loss: `spiqa_540`

- The candidate retrieved the correct Figure 3 at rank one.
- Its OCR states the relevant `L = 9` values and identifies DMRNet as best.
- The Worker nevertheless interpreted the panels as `L=12` and `L=96`, then
  claimed the requested result was unavailable.
- The identical reader on the richer teacher graph answered `DMRNet`.

This shows that retaining and retrieving a raw image does not guarantee equal
downstream performance. Graph-produced visual summaries and contextualization
can change whether the Worker successfully reads the evidence.

### 7.2 Repaired but unstable: `spiqa_378`

The candidate retrieved the decisive table at rank one. One Worker read the
correct DLA values, while another confused the NoCorrect row and calculated
zero improvement. Global refinement eventually recovered the exact answer,
but latency increased from 40.30 to 155.52 seconds.

### 7.3 Correct but unnecessarily expensive: `spiqa_542`

Both graphs produced `RCE`, but candidate-graph latency rose from 21.08 to
86.02 seconds because of an unnecessary adjustment round.

### 7.4 Consequence

The safe scheduling/redundancy changes do not intrinsically discard raw
evidence. The main observed risk is the smaller construction model and more
compressed visual/evolution metadata. A claim of “21× faster with no
performance loss” is rejected by the current evidence.

## 8. Structured-output findings

### 8.1 Small models can produce reliable JSON when the server enforces it

The conservative 8B server passed 40/40 constrained responses with valid JSON
and valid schemas. This resolves the earlier Qwen2.5-VL-7B experience where
`response_format={"type":"json_object"}` was accepted by the API but not
actually enforced by the local server.

Reliable structured output requires both:

1. a server/decoder that enforces a grammar or JSON schema; and
2. code that supplies a schema matching the consumer's real field contract.

The official preprocessing prompt requested three image fields, while the
consumer unconditionally read a fourth, `text_content`. Strict enforcement
exposed this latent producer/consumer mismatch.

### 8.2 A better model is not a substitute for a constrained interface

The matched 32B replay of `spiqa_96` still generated invalid Planning Graph
JSON on every retry. Larger models reduce some semantic errors, but they do not
guarantee syntactically valid machine interfaces.

### 8.3 Tolerant recovery must remain narrow

The audit recovered an answer only when an explicit opening `<output>` tag was
present and the missing closing tag was the sole defect. Free-form thought text
was never silently promoted to an answer. This preserves audit integrity while
showing exactly what the frozen parser lost.

## 9. Model sensitivity and what can be attributed to G²

Eleven selected cases were replayed with the 32B online reader on the exact same
optimized-8B Content Graph:

- completed: 11/11;
- official parser successes: 11/11;
- semantically correct 32B answers: 5/11 before later raw-source corrections;
- 8B-incorrect cases repaired by 32B: 4;
- 8B-correct cases regressed by 32B: 0.

Interpretation:

- Some Worker and parser behavior is model-sensitive.
- A stronger reader repairs some cases, but not all.
- `spiqa_44`, `spiqa_571`, and `spiqa_47` remained wrong under the matched 32B
  reader, supporting system-level planning/composition concerns.
- `spiqa_96` reproduces an official structured-interface defect with 32B.
- These replays do not measure an end-to-end original 32B baseline because the
  underlying Content Graph remains the optimized-8B graph.

Therefore, the audit distinguishes three claims:

- **Observed in the low-resource configuration:** supported for all corrected
  counts.
- **Sensitive to reader model:** supported when matched 32B changes the result.
- **Intrinsic to the official G² design/integration:** requires reproduction
  on the official path; currently strongest for structured parsing and some
  planning/composition failures.

## 10. Repeatability and operational variance

Fixed seeds improved experimental control but did not make the complete system
perfectly deterministic. `spiqa_540` failed in one matched candidate-graph run
and answered correctly in a later audit replay with the nominally same graph,
model, and seed.

Possible sources include concurrent request scheduling, backend kernel
nondeterminism, changed refinement trajectory after small textual differences,
or service/runtime state. A single successful rerun must not erase a recorded
failure. Production evaluation should report repeated-run stability in addition
to one-shot accuracy.

## 11. Scalability implications

The Content Graph itself does not depend on the question. The practical
scalability problem is the current experiment/application organization:
graphs are constructed and cached for question-specific document bundles,
rather than maintaining one deduplicated graph artifact per stable document or
collection version.

At the measured optimized mean of 160.85 seconds, 17,000 sequential cold graph
builds would take roughly 31.6 days. This is only an extrapolation—not a
measured 17,000-document benchmark—but it shows that rebuilding overlapping
document bundles per question is not viable.

A scalable deployment needs:

- document/content-hash keyed analysis and embedding caches;
- incremental graph construction when documents change;
- deduplication across question bundles;
- persistent graph/index loading independent of question ID;
- distributed or batched offline ingestion;
- an online path that only retrieves and reasons over already-built artifacts.

Additional HDD/NFS space is useful for these persistent caches. It does not
replace GPU compute or eliminate the hundreds of VLM calls required by cold
construction.

## 12. Recommended repair order

### 12.1 First scientific repair: evidence-grounded Workers

Worker support is the dominant corrected category, especially for tables,
figures, values, and trends. The first controlled repair should require each
Worker to return:

- its answer;
- cited retrieved node IDs;
- extracted values and labels;
- units;
- the requested arithmetic/comparison operation.

The runtime should then:

1. verify that every cited node was actually retrieved;
2. verify labels, values, and units against cited evidence;
3. execute numerical operations deterministically;
4. rerun only the failed Worker with focused rows/columns or a zoomed visual;
5. recompute only Planning Graph ancestors that depend on the corrected task;
6. use existing global replanning only if local repair fails.

This proposal is supported by the 20 Worker failures and the 18/20
table/figure/value/trend signal. It must still be tested against an unchanged
baseline before being claimed as an improvement.

### 12.2 Interface reliability repair

Separately from scientific reasoning quality:

- require schemas for Planning Graph and checker outputs;
- align prompt schemas with consumer-required fields;
- cap output sizes according to the actual contract;
- distinguish `unparseable` from `insufficient` instead of automatically
  triggering global replanning;
- accept a complete explicit `<output>` body at end-of-stream when only the
  closing tag is missing, while never promoting hidden thought text.

### 12.3 Visual metadata repair

Compare teacher and student analysis on the decisive visual nodes, especially
`spiqa_540`. Replay identical Worker prompts with:

- raw image plus 32B teacher summary;
- raw image plus 8B student summary;
- raw image alone.

Only after localizing the minimum missing capability should a selective teacher
fallback or distilled visual analyzer be introduced.

### 12.4 Efficiency repair

Replace unconditional global refinement with local dependency-aware repair.
Cache all query-independent document artifacts by content hash. Measure both
cold construction and cached-query latency, because the fast candidate graph
currently makes online inference slower in several cases.

## 13. What the current evidence does and does not prove

Supported conclusions:

- optimized construction is dramatically faster on the tested L40S setup;
- all five optimized pilot builds finished below three minutes;
- decisive top-5 evidence was retained in the five paired cases;
- operational answer quality was lower on candidate graphs;
- Worker evidence use is the largest observed failure class in the 100-case
  low-resource audit;
- the released parser/structured-output integration has reproducible defects;
- five benchmark rows are unsuitable for accuracy scoring.

Unsupported or premature conclusions:

- that the optimized builder has no quality loss;
- that 65/95 is the accuracy of original end-to-end 32B G²;
- that every low-resource Worker failure is intrinsic to G²;
- that the five-question loss rate estimates dataset-wide accuracy;
- that all four visually identified semantic benchmark defects are ready for
  publication without independent human confirmation;
- that a 17,000-document deployment has been benchmarked.

## 14. Source reports and precedence

The consolidated conclusions above derive from:

- [`low_resource_content_graph/REPORT.md`](low_resource_content_graph/REPORT.md)
  — construction optimization timeline and three-case gate;
- [`low_resource_content_graph/loss_evaluation/REPORT.md`](low_resource_content_graph/loss_evaluation/REPORT.md)
  — five-case teacher/candidate graph comparison;
- [`failure_audit_100/REPORT.md`](failure_audit_100/REPORT.md)
  — resumable run protocol and execution record;
- [`failure_audit_100/posthoc_adjudication/POSTHOC_REPORT.md`](failure_audit_100/posthoc_adjudication/POSTHOC_REPORT.md)
  — corrected aggregate audit;
- [`failure_audit_100/posthoc_adjudication/PARSER_RECOVERY.md`](failure_audit_100/posthoc_adjudication/PARSER_RECOVERY.md)
  — narrow recovery of unclosed explicit outputs;
- [`failure_audit_100/posthoc_adjudication/REPLAY_ADJUDICATION.md`](failure_audit_100/posthoc_adjudication/REPLAY_ADJUDICATION.md)
  — matched 32B reader comparisons;
- [`failure_audit_100/posthoc_adjudication/DATA_INTEGRITY.md`](failure_audit_100/posthoc_adjudication/DATA_INTEGRITY.md)
  — invalid benchmark rows and `spiqa_96` reproduction;
- [`failure_audit_100/posthoc_adjudication/visual_validation/VISUAL_VALIDATION.md`](failure_audit_100/posthoc_adjudication/visual_validation/VISUAL_VALIDATION.md)
  — final raw-image corrections for 12 disputed cases.

Precedence for disputed labels is:

```text
raw source/image validation
  > evidence-backed trace adjudication
  > semantic answer adjudication
  > lexical or exact-match screening
```


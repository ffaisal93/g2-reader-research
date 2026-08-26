# G² Baseline Runtime and Failure Audit

## Purpose

This report explains the existing one-question results before any new reasoning
method is introduced. It distinguishes the G² research architecture, the
patched released implementation, and the independent minimal implementation.
It does not propose a question-specific planner, deterministic table filter,
counting shortcut, or replacement RAG architecture.

## Artifacts audited

Minimal implementation:

    results/smoke/runs/minimal_matched_plumbing_20260818T0108/
      run_manifest.json
      predictions.jsonl
      traces/feta_tab_10447.json
      traces/feta_tab_10447.md

Patched released implementation:

    results/smoke/runs/corrected_real_plumbing_v9/
    results/comparisons/per_question.jsonl

Question and reference:

    Question:  How many of the songs are from 1979?
    Reference: Four are from 1979 (...)

Both audited implementations predicted 1.

## Architecture being tested

    MinerU document elements
      -> multimodal Content Graph
      -> question-time graph retrieval
      -> model-generated Planning Graph
      -> dependency-ordered Workers
      -> evidence sufficiency check
      -> bounded plan refinement/re-execution
      -> final synthesis

This is distinct from the separate one-call production RAG path. Results from
that path are not G² baseline results.

## Exact minimal-run measurements

The complete minimal run took **1,018.556 seconds**, or **16.976 minutes**. It
contained graph construction and question-time inference in one trace.

    Content Graph nodes:       13
    Initial retrieved nodes:    5
    Initial induced edges:     28
    Planning Graph nodes:       9
    Planning Graph edges:       7
    Execution rounds:           4
    Worker calls:              36
    Total recorded calls:     110
    Total model-call time:    982.580 seconds
    Non-call orchestration:    35.975 seconds
    Total input tokens:       179,735
    Total output tokens:       15,769
    Total tokens:             195,504
    Peak recorded VRAM:        31,233,342,464 bytes
    Final prediction:           1

### Runtime by role

| Role | Calls | Seconds | Share of wall time |
|---|---:|---:|---:|
| Node analysis | 13 | 82.549 | 8.10% |
| Content Graph evolution | 13 | 119.067 | 11.69% |
| Embeddings | 39 | 1.407 | 0.14% |
| Planning | 1 | 30.026 | 2.95% |
| Workers | 36 | 662.965 | 65.09% |
| Evidence checking | 4 | 28.644 | 2.81% |
| Planning refinement | 3 | 44.743 | 4.39% |
| Final synthesis | 1 | 13.180 | 1.29% |
| Non-call orchestration | — | 35.975 | 3.53% |

Workers dominate runtime. Embedding generation is not the bottleneck here.

### Cost of each execution round

| Round | Worker calls | Worker seconds | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| 0 | 9 | 165.199 | 34,436 | 2,439 |
| 1 | 9 | 169.810 | 34,436 | 2,439 |
| 2 | 9 | 163.688 | 34,436 | 2,439 |
| 3 | 9 | 164.268 | 34,436 | 2,439 |

The three refinement rounds added 27 Worker calls and approximately 497.766
Worker seconds. Their identical token counts indicate that the plan, evidence,
and answers did not materially change.

## Why the minimal implementation failed

### 1. Node labels replaced actionable tasks

The graph contained song-named node IDs such as Armagideon Time and Justice
Tonight, but every node's task was the literal string Single. The Planner did
not create atomic evidence-selection, comparison, or aggregation subquestions.
Retrieval and Worker prompts consume the task field, not the meaningful-looking
node ID.

### 2. Every Worker retrieved with the same query

All 36 per-task retrievals used query = Single and selected the same five
Content Graph nodes. The highest-ranked node was a chart/peak-position table.
The required release table with four 1979 rows was outside the five-node Worker
result.

The initial question probe did contain the correct release table. Evidence was
available to the Planner, but bad task strings caused Workers to retrieve less
relevant evidence.

### 3. Every Worker produced the same answer

Within each round, all nine Worker answers were identical. Across all four
rounds, answer content and evidence-node sets remained identical. Workers
summarized chart positions instead of resolving the original count.

Dependencies executed children before parents, but prerequisites could not add
useful information because each child returned the same chart summary.

### 4. The checker identified the problem but could not repair it

The checker consistently said peak-position answers did not provide the number
of songs from 1979. That judgment was correct.

In this historical trace, a scalar gaps string was split into characters. The
current agents.check implementation contains a regression fix that wraps a
scalar string as one gap. The historical trace correctly preserves what
happened and was not overwritten.

### 5. Refinement changed nothing

There were four Planning Graph snapshots and four execution orders, but only
one unique graph and one unique order. The pipeline then re-executed the entire
unchanged graph after each insufficient judgment.

This explains both latency and lack of improvement: three more executions ran
without changing queries, evidence, dependencies, or answers.

### 6. Final synthesis amplified duplication

Final synthesis received all 36 intermediate answers, not only the last round.
They were duplicates of the same incorrect chart summary. The final model saw
repetition rather than independent evidence and returned 1.

## Minimal implementation versus original Planner contract

This does not prove that original G² always creates Single tasks.

The released Planner prompt requires:

- a root node containing the original question;
- specific, atomic sub-tasks;
- six or fewer nodes;
- maximum depth three;
- explicit node children and edges.

The minimal Planner prompt asks only for compact JSON nodes and edges with an ID
and task. It does not reproduce the released root, atomicity, node-count, depth,
type, or child-list requirements. The measured nine-node graph has no root.

There is a second execution-contract difference: the released runtime treats
the root as the original question and skips it during per-node Worker
execution, then performs final aggregation. The minimal pipeline currently
executes every node, including a node named root, and later performs final
synthesis as well. Once root validation is restored, this would add a redundant
root Worker call unless the execution loop is aligned too.

The evidence-check and refinement inputs also differ:

- The released checker receives the original question, initial retrieved
  context, and current-round subtask question/answer pairs.
- The minimal checker receives the question and a flat list of answer strings,
  without initial context, task text, evidence IDs, or source content.
- The released refiner receives original context, current question/answer
  evidence, concrete gaps, and the old DAG.
- The minimal refiner receives only the question, gaps, and old graph.
- The released final reasoner receives initial retrieved context plus the
  execution trajectory; the minimal synthesizer receives the trajectory but
  not the initial retrieved context or images.

The minimal refiner was therefore asked to repair an evidence-coverage problem
without being shown the evidence or the retrieval context. This is a direct
explanation for unchanged refinements and another baseline-fidelity issue.

This run therefore measures the current minimal Planner contract, not a
prompt-faithful reproduction of the released Planner.

Aligning prompt, schema, and validation with the released contract is a
**baseline-fidelity repair**, not a new scientific method. Hard-coding a plan
for counting questions would be a method change and remains out of scope.

## Patched released-run findings

The patched released run took **214.707 seconds** online while reusing an
offline Content Graph. Its Planner failed strict structural validation on three
attempts, then used the documented single-root fallback and returned 1.

The two implementations therefore had different Planner failures:

    minimal:          accepted a valid-shaped but semantically useless plan
    patched released: rejected invalid plans and used a one-root fallback

The timings are not directly comparable because the minimal trace includes
Content Graph construction while the released run reused its graph.

## Baseline-fidelity repair result

The generic fidelity repairs were evaluated against the same frozen 13-node
Content Graph. No benchmark-ID rule, question-type branch, deterministic table
filter, or deterministic counting operator was added.

The repaired boundary now:

- requires a rooted, connected, bounded dependency DAG;
- retries syntactically valid but operationally invalid role output;
- skips the root Worker, as the released runtime does;
- gives the checker and refiner initial context plus task/answer evidence;
- gives final synthesis initial context and images;
- labels retrieved nodes as `Related Memory [i]`, retaining node/source IDs;
- asks Workers to ground claims in those labels and use completed child answers;
- records structured-output validation failures and response previews.

Runs `minimal_baseline_fidelity_v2` through `v4` returned the correct text, but
they are **not valid Planning Graph successes**. In all three, each Planner
attempt produced an unusable 1,021-token response and the bounded retry policy
fell back to a root-only graph. Final synthesis then answered directly from the
initial table evidence. These runs are retained as fallback diagnostics, not
accuracy evidence for G² decomposition.

Run `minimal_baseline_fidelity_v5` is the first clean non-fallback run after the
repair:

| Measure | Result |
|---|---:|
| Warm question-time duration | 74.892 s |
| Planning rounds | 1 |
| Planning nodes | 3 (root + 2 subtasks) |
| Worker calls | 2 |
| Structured Planner attempts | 1 |
| Planner output tokens | 201 |
| Prediction | `1` |
| Reference | `four` |
| Correct | No |

The accepted v5 graph was:

    root: How many of the songs are from 1979?
      -> n-1: Find the chart data for 'London Calling' in 1979.
           -> n-2: Count the number of songs from 1979.

Because edges mean that a parent consumes its child's answer, execution was
`n-2`, `n-1`, then `root`. This dependency is semantically backward: the count
ran before receiving any fact-selection result, while the chart-data task
consumed the count.

The `n-2` retrieval selected the chart-history table rather than the release
table containing four 1979 rows. The Worker then correctly counted one 1979
row in the wrong table. The next Worker converted that result into chart data.
Finally, the evidence checker confused the requested song count with chart
position evidence and marked the trajectory sufficient, so refinement never
ran.

Compared with the historical 1,018.556-second end-to-end trace, v5 is about
13.6 times faster in observed wall time. This ratio is directional rather than
an offline/online benchmark because the historical run included Content Graph
construction and v5 reused a frozen graph. The valid conclusion is that
removing redundant full-plan rounds and generic `Single` Workers greatly
reduces latency, while the remaining Planner/retrieval/checker errors still
prevent a correct baseline answer.

## Follow-up frozen evaluations (v6-v10)

Further work remained generic and architecture-preserving:

- restored released behavior where a checker response missing `sufficient`
  defaults conservatively to false;
- made `semantic_candidates` operational by interleaving several semantic
  entry points with local graph neighbors instead of allowing the first seed
  to consume the complete evidence budget;
- ordered local neighbors by same-document element distance, semantic score,
  and stable ID rather than arbitrary node-ID order;
- rendered MinerU HTML tables as lossless labeled rows before model inference;
- retained the same five-node evidence budget and frozen Content Graph;
- added no deterministic filtering, counting, or benchmark-specific branch.

The successive `feta_tab_10447` results were:

| Run | Valid DAG | Duration | Prediction | Main observation |
|---|---:|---:|---:|---|
| v6 | Yes | 148.289 s | `1` | Wrong chart table; checker accepted duplicated wrong answers. |
| v7 | Yes | 70.107 s | `1` | Correct release table retrieved, but records were collapsed into one song. |
| v8 | Yes | 110.011 s | `2` | Both tables read, but the model mixed table/entity semantics. |
| v9 | No | 254.045 s | `1` | Row labels caused over-decomposition; three oversized plans fell back to root. |
| v10 | Yes | 68.431 s | `7` | Model misclassified 1980 chart rows as 1979 and added across unrelated tables. |

The v10 Planner obeyed the released six-node/depth-three bound and used one
round with two Workers. The release node containing all four 1979 rows was in
the counting Worker's evidence. The remaining error was therefore not evidence
absence: the 7B VLM misread row values and combined incompatible units, while
the checker repeated the incorrect claim and declared it sufficient.

This sequence is important negative evidence. Once the correct node is
retrieved and its table is rendered clearly, repeatedly tuning a prompt against
this one benchmark item risks overfitting and no longer establishes general G²
quality. Work on this item stopped after v10.

## Second frozen question

The only other already-ingested frozen graph was `paper_tab_125`:

    Question: What baseline and alternative architectures, including those
              that utilize single and concatenated word embeddings, are
              compared to MGNC-CNN according to the study?
    Reference: standard CNN, C-CNN, MVCNN

The historical minimal run took 382.205 seconds, executed 64 calls over four
identical rounds, and failed to list the requested comparison architectures.

The repaired `minimal_baseline_fidelity_paper_v3` run:

- completed in **233.469 seconds**;
- used one valid six-node Planning Graph and one execution round;
- made five Worker calls;
- required no transport retry in the successful run;
- mentioned a basic/single-embedding CNN, CCNN, and MVCNN;
- incorrectly added MG-CNN and included unrelated performance discussion;
- scored `exact_match=0` and `contains_reference=0` under the repository's
  deterministic evaluator.

This is faster and semantically closer, but still not benchmark-correct. Its
Planning Graph also placed a performance-comparison task as a child dependency
of every architecture-identification task, another example of the 7B Planner
reversing useful information flow despite an explicit dependency contract.

An earlier attempt at this second question encountered CUDA OOM because another
Python process held approximately 8.9 GiB on the same GPU. The minimal client
now disables opaque SDK retry and records up to two explicit retries for HTTP
429/5xx failures. The successful rerun needed no retry. The unrelated process
was not terminated.

## Five-dataset frozen smoke evaluation

The evaluation was then extended to one frozen question from each smoke-slice
dataset. All five questions now have persisted Content Graphs, so later runs
can measure question-time behavior without rebuilding document memory. The
SlideVQA, SPIQA, and SciGraphQA graphs contain 24, 41, and 109 nodes,
respectively. The SciGraphQA item spans eight documents.

These are five case studies, not a benchmark score. They expose runtime and
failure modes across table, slide, and scientific-figure evidence, but are far
too small for a quality claim.

| Dataset / question | Persisted graph | Warm online time | Rounds / Workers | Result |
|---|---:|---:|---:|---|
| FeTaQA `feta_tab_10447` | 13 nodes | 68.431 s | 1 / 2 | Wrong: `7`; reference `four` |
| PaperTab `paper_tab_125` | existing frozen graph | 233.469 s | 1 / 5 | Semantically close but over-inclusive; deterministic metrics 0 |
| SlideVQA `slidevqa_521` | 24 nodes | 115.797 s | 1 / 4 | Wrong: `2015`; reference `2014` |
| SPIQA `spiqa_342` | 41 nodes | 96.102 s | 1 / 2 | Correct: `2` |
| SciGraphQA `scgqa_176` | 109 nodes | 128.948 s | 1 / 4 | Correct direction, but omitted the reference explanation |

Under the repository's strict exact/containment evaluator, only SPIQA passes:
**1/5 exact and 1/5 containment**. The SciGraphQA response captures the core
comparison—8-OK decays more than 8-KF-RTRL-AVG as network size grows—but it
does not reproduce the causal explanation in the reference, so it is reported
as directionally correct and incomplete rather than benchmark-correct.

### Offline construction versus online answering

The newly ingested first runs included both graph construction and answering:

| Dataset | Nodes | Edges | First end-to-end time | Graph-analysis/evolution calls |
|---|---:|---:|---:|---:|
| SlideVQA | 24 | 149 | 828.591 s | 48 |
| SPIQA | 41 | 280 | 722.172 s | 82 |
| SciGraphQA | 109 | 729 | 1,952.837 s | 218 |

For SPIQA, node analysis plus graph evolution consumed 570.191 seconds. For
SciGraphQA those stages consumed 1,275.623 seconds. This confirms that Content
Graph construction is a large one-time offline cost and must not be included
in a production query-latency number. Persisting and reusing the graphs reduced
the observed runs to 96.102 and 128.948 seconds, respectively, without
changing the research method.

### Generic no-progress termination

The historical SlideVQA trace performed four identical execution rounds: 16
Worker calls with three refinements that did not change the effective plan. A
generic termination guard now compares the executable graph—node IDs, task
texts, and edges—and stops when refinement changes no executable work. It
ignores metadata-only changes such as a node `kind` label.

With the same graph and model, the warm SlideVQA run fell from 201.336 seconds
and two rounds under the first guard to 115.797 seconds and one round under the
effective-plan guard. Its answer remained `2015`, so this is a runtime repair,
not an accuracy improvement or a new reasoning method.

The warm SPIQA run also stopped after one unchanged refinement. SciGraphQA's
checker marked its first-round evidence sufficient, so no refinement call was
needed.

### Dataset-specific observations

- **SlideVQA:** retrieved evidence/model output associated 46% with 2015 and
  72% with 2014, while the reference answer is 2014. The checker rationale was
  internally contradictory. The trace is retained as a benchmark/model
  disagreement requiring dataset-level inspection, not silently corrected.
- **SPIQA:** returned the reference answer `2` on both the full first run and
  the warm persisted-graph run. This is the first strict success in the frozen
  five-question slice.
- **SciGraphQA:** retrieved enough figure context to state the correct relative
  trend, but final synthesis omitted why larger networks reduce 8-OK's
  advantage. This is an answer-completeness failure rather than a reversal of
  the visual comparison.

No transport retry was required in these successful runs. The complete
minimal-plus-patched-baseline test suite passes: **51 passed**, with two
pre-existing deprecation warnings.

## Conclusions

1. The 17-minute runtime is real for the audited minimal configuration.
2. Sequential Workers and full-plan refinement dominate latency.
3. The correct table was present during initial retrieval.
4. The minimal Planner contract admitted a useless graph.
5. Refinement did not alter the plan or evidence.
6. Both implementations failed through different Planner paths.
7. Five questions still cannot establish benchmark-level G² accuracy; the
   strict frozen result is currently 1/5.
8. Persisted graphs remove a very large offline cost, but 68-233 seconds per
   warm query remains unsuitable for a conventional production RAG latency
   target.
9. Generic unchanged-plan termination removes redundant work without changing
   the research idea, but sequential multi-agent generation remains the main
   online bottleneck.
10. The failures now include backward dependencies, table/entity
    misinterpretation, false-positive sufficiency judgments, and incomplete
    final synthesis—not merely missing retrieval evidence.

## Completed baseline-alignment steps

1. The Planner now enforces the released root, atomicity, node-count, depth,
   connectivity, and dependency-DAG contract.
2. Root execution is aligned: non-root tasks run first and final synthesis
   performs aggregation.
3. Checker and refiner inputs include initial context and labeled task/answer
   evidence.
4. Final synthesis retains initial text and image evidence.
5. Offline graph construction and warm inference are reported separately.
6. Structured-output retries, transport retries, termination reasons, and
   effective unchanged refinements are explicit in traces.
7. The five frozen questions were run without benchmark-ID or question-type
   branches.

## Remaining baseline work

1. Evaluate a substantially larger frozen slice before drawing quality
   conclusions.
2. Add retrieval recall, citation/faithfulness, numerical correctness, and
   multimodal judge metrics alongside exact match.
3. Measure dependency-level Worker concurrency as a runtime-only ablation;
   retain identical tasks, evidence budgets, and model prompts.
4. Diagnose Planner edge direction and checker calibration across the larger
   slice rather than tuning against one example.
5. Keep research-faithful G² and any future production or scientific-module
   variants as separately named, separately evaluated paths.

Only after a prompt-faithful baseline exists should runtime tuning be measured.
Safe candidates include resident models, reused question-independent Content
Graphs, batched embeddings, and concurrent dependency-independent Workers.
Changing retrieval budgets, refinement limits, planning limits, evidence, or
reasoning operators must be reported as ablations or new methods.

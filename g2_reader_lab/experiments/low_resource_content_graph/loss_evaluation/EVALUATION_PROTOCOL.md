# 32B Teacher vs Optimized 8B Content Graph: Fixed Evaluation Protocol

## Purpose

Measure what is lost when the optimized low-resource Content Graph builder uses
Qwen3-VL-8B-Instruct-FP8 instead of the saved official-style
Qwen3-VL-32B-Instruct-FP8 teacher.

This is a five-question matched pilot. It is not a dataset-level accuracy
estimate.

## Fixed evaluation set

The set is fixed before running the new experiments. These are all questions
for which a completed 32B teacher graph exists in
`memory_systems_qwen3_official_fixedseed_v5`:

1. `spiqa_58` — figure plus explanatory text;
2. `spiqa_108` — multi-line chart;
3. `spiqa_378` — numerical table;
4. `spiqa_540` — figure/formula comparison;
5. `spiqa_542` — numerical table/figure lookup.

## Controlled configurations

### Teacher graph

- Builder: Qwen3-VL-32B-Instruct-FP8
- Saved graph: official traced fixed-seed pilot, iteration 1
- Evolution rounds: 1
- Retrieval budget: 5
- Seed: 42

### Candidate graph

- Builder: Qwen3-VL-8B-Instruct-FP8
- Implementation: `student_8b_behavior_preserving`
- Evolution rounds: 1
- Retrieval budget: 5
- Seed: 42
- Every extracted node retained
- One evolution call per node
- No question-dependent filtering or selective evolution

## Comparisons

### A. Construction comparison

For each question record:

- node count;
- construction wall time;
- VLM calls and tokens;
- embedding calls and tokens;
- structured-output or fallback events.

### B. Retrieval comparison

Embed the identical question with the same BGE-M3 endpoint and run the same
official top-5 semantic-plus-link expansion over both graphs. Record:

- raw-node overlap@5;
- teacher traced text-evidence hits;
- whether the decisive reference evidence is present;
- rank and modality of decisive evidence;
- cases where the candidate retrieves a related but wrong table/figure.

Raw overlap is diagnostic, not an accuracy metric: two different nodes can
contain equivalent evidence.

### C. Graph-isolated QA comparison

Run the same Qwen3-VL-8B online Planning Graph/Worker/sufficiency/final-answer
pipeline over the saved teacher graph and candidate graph. Keep top-k and
runtime settings fixed. This isolates graph-construction loss from online
answer-model loss as far as the stochastic official pipeline permits.

Record:

- parsed prediction and raw final response;
- exact match for short lookup answers;
- semantic correctness against the reference;
- numerical/entity correctness;
- whether the answer is supported by retrieved evidence;
- parser or sufficiency failures;
- cached-query latency.

### D. Saved full-pipeline teacher comparison

Report the previously saved 32B teacher prediction separately. This comparison
includes both graph-builder and online-model differences and must not be called
graph-isolated loss.

## Predeclared interpretation

- A candidate loss is confirmed when the teacher graph supplies decisive
  evidence or a correct answer under the matched online reader and the
  candidate does not.
- An online-model/parser loss is not attributed to graph construction when the
  candidate retrieved the decisive evidence but the shared online reader
  failed to use or parse it.
- A raw top-5 overlap reduction alone is not a quality loss when both retrieved
  sets contain sufficient, equivalent evidence.
- Results will be reported question by question; the sample is too small for a
  production or no-regression claim.


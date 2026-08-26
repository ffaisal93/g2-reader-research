# SPIQA-100 G2 Failure Audit: Post-Hoc Report

## Current conclusion

The execution pass, semantic/trace adjudication, and raw visual validation are complete.
Targeted matched-32B replay is complete.
Counts below describe the optimized-8B configuration. Matched 32B replay
separates some reader-model sensitivity, but this is not an end-to-end
original-32B baseline.

## Data integrity

- Requested slice: **100** questions
- Invalid benchmark rows excluded: **5** (spiqa_164, spiqa_195, spiqa_281, spiqa_452, spiqa_79)
- Valid denominator: **95**

## Answer outcomes after cross-validation

- Officially parsed and semantically correct: **59/95**
- Additional semantically correct raw answers lost by parser: **6**
- Raw/candidate answer correctness: **65/95**
- Incorrect or no-answer outcomes: **30**
- Ambiguous valid outcomes: **0**

The semantic screen used structured Qwen3-VL-32B adjudication. Suspected
errors then received a second evidence-backed trace judgment, which corrected
12 over-strict reference-matching false positives plus one recovered-output case.

## Primary failure categories

- `worker_support_failure`: **20** — `spiqa_0`, `spiqa_110`, `spiqa_116`, `spiqa_18`, `spiqa_181`, `spiqa_196`, `spiqa_222`, `spiqa_245`, `spiqa_34`, `spiqa_347`, `spiqa_368`, `spiqa_381`, `spiqa_392`, `spiqa_4`, `spiqa_434`, `spiqa_440`, `spiqa_522`, `spiqa_585`, `spiqa_586`, `spiqa_98`
- `parser_failure`: **9** — `spiqa_223`, `spiqa_249`, `spiqa_26`, `spiqa_272`, `spiqa_29`, `spiqa_39`, `spiqa_55`, `spiqa_61`, `spiqa_96`
- `retrieval_failure`: **4** — `spiqa_292`, `spiqa_396`, `spiqa_510`, `spiqa_578`
- `decomposition_failure`: **2** — `spiqa_44`, `spiqa_571`
- `composition_failure`: **1** — `spiqa_47`

## Dominant repair signal

Worker-support failures remain the largest class (**20**).
A conservative keyword screen finds table/figure/value/trend language in **18/20**
classification rationales. This supports—but does not yet finalize—the
planned evidence-node citation, value/unit verification, deterministic
calculation, and local Worker repair experiment.

## Required validation

- Raw visual cases completed: **12/12**
- Raw visual cases still unresolved: **0**
- Targeted 32B replays complete: **11/11**
- Targeted 32B replays failed: **0**
- Replay currently running: **none**
- `spiqa_96` separately reproduced its malformed Planning Graph JSON with
  the 32B reader on all 15 official retries.

## Matched-reader result

- Replays semantically adjudicated: **11/11**
- Official parser successes: **11/11**
- Semantically correct 32B answers: **5/11**
- 8B-incorrect cases repaired by 32B: **4**
- 8B-correct cases regressed under 32B: **0**

These matched replays hold the Content Graph fixed, so they isolate
reader/model sensitivity rather than graph-construction quality.

## Raw visual validation result

- Two provisional errors (`spiqa_163`, `spiqa_215`) were restored as correct.
- Four cases (`spiqa_164`, `spiqa_195`, `spiqa_281`, `spiqa_452`)
  were excluded because the benchmark question/reference conflicts with the source.
- `spiqa_368` moved from retrieval to Worker support; `spiqa_578` moved
  from Worker support to retrieval; `spiqa_98` moved from parser-only
  to Worker support with parser as secondary.
- The four new dataset-failure decisions should receive independent
  human confirmation before publication.

## Artifacts

- `OUTCOMES.jsonl`: immutable-source outcome inventory
- `PARSER_RECOVERY.md`: derived unclosed-output recovery
- `SEMANTIC_ADJUDICATION.md`: first-pass semantic judgments
- `CAUSAL_CLASSIFICATION.md`: evidence-backed causal judgments
- `DATA_INTEGRITY.md`: invalid-row and matched parser findings
- `REPLAY_ADJUDICATION.md`: matched 32B reader comparison
- `visual_validation/VISUAL_VALIDATION.md`: source-grounded raw-image review
- `teacher_replays/`: matched 32B reader outputs on identical 8B graphs

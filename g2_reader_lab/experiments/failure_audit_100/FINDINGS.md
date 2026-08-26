## Findings recorded during execution

### Gate case: `spiqa_542`

- The existing optimized-8B graph loaded correctly and the official online G2
  path returned the reference answer, `RCE`.
- The initial Worker had the decisive table in its context and could identify
  the `RCE = 0.77` row, but its response became distracted by a different
  high-confidence C&W-wb table containing `100, 100`.
- The round-0 sufficiency response began with `<check>` but was truncated before
  producing a complete parseable block. Official G2 therefore recorded
  `parsed=false`, treated the answer as insufficient, and refined globally.
- The run expanded to four Planning Graph executions, 13 Worker results, four
  sufficiency checks, and 22 recorded online model calls before returning the
  correct final answer.
- Cached-query time was 180.92 seconds. This is a confirmed parser/refinement
  efficiency failure, not a final-answer failure. Whether the same behavior is
  specific to the 8B model must remain a separate teacher-validation question.

### Early replay observations: `spiqa_540`, `spiqa_108`, and `spiqa_378`

- `spiqa_540` returned the correct `DMRNet` answer in this audit replay even
  though the earlier matched candidate-graph run answered that the result was
  unavailable. The graph, nominal model, and seed are the same. This is direct
  evidence of operational run-to-run variance; it does not erase the earlier
  failure.
- `spiqa_108` returned a semantically correct answer but used four Planning
  Graph executions, 14 Worker results, and 24 online model calls. This repeats
  the excessive-refinement symptom without repeating the previous missing
  final `</output>` parse failure.
- `spiqa_378` also returned a semantically correct answer, but used four
  Planning Graph executions and 22 online model calls. Three sufficiency-check
  responses were unparseable, so the official fallback repeatedly treated the
  evidence as insufficient.
- These are currently classified only as parser/refinement efficiency signals.
  Any claim that they are intrinsic original-32B G2 failures still requires a
  matched teacher replay.

### Reproducible Planning Graph serialization failures

- `spiqa_79` exhausted three complete query attempts. Within each attempt, all
  three DAG-generation rounds and five retries per round returned the same
  truncated JSON string (`Unterminated string`). No valid Planning Graph was
  produced, so the official online path raised `RuntimeError` before Worker
  execution.
- `spiqa_96` likewise exhausted three query attempts. Its generated Planning
  Graph repeatedly contained an invalid JSON backslash escape, and all DAG
  parser retries failed before Worker execution.
- Both graphs were built correctly, the VLM endpoint remained healthy, and
  subsequent questions continued. These are confirmed structured-output /
  Planning Graph serialization failures in this 8B configuration, not Content
  Graph construction, retrieval, or GPU failures.
- The frozen behavior has not been repaired during the audit. The failed cases
  remain available for later matched 32B replay and structured-output repair
  evaluation.

### Execution-phase completion

- The resumable SPIQA-100 pass completed on 2026-08-25. All **100 Content
  Graphs** were built; **98 online queries** produced complete trace/output
  artifacts, and the two Planning Graph serialization cases above exhausted
  their retries.
- Mean new Content Graph construction time was **160.85 seconds** and mean
  completed online-query time was **71.82 seconds** in this optimized-8B
  configuration.
- **18/98 completed queries** contain a nonempty raw final response but no
  parsed prediction. These are final-output parser candidates, not automatically
  18 incorrect raw answers.
- Behavior-neutral trace screening found **21** multi-refinement cases and
  **4** questions with intermediate sufficiency-parser signals. It generated
  review packets for **79** conservatively flagged questions.
- The 79 packets are a review queue, not an error count: lexical mismatch flags
  include semantically correct paraphrases. Causal error attribution and matched
  original-32B replay remain the next experiment phase.

## Post-hoc audit completion (2026-08-26)

Raw-source validation reduced the benchmark denominator from 100 to **95**:
`spiqa_79`, `spiqa_164`, `spiqa_195`, `spiqa_281`, and `spiqa_452` are dataset
or question/reference failures. The optimized-8B result is **65/95** correct
parsed/recoverable raw answers and **30/95** incorrect/no-answer outcomes. Six
correct raw answers were lost by the official final-output parser.

Corrected failure phenomena are Worker support **20**, parser **9**, retrieval
**4**, decomposition **2**, and composition **1**. See
`posthoc_adjudication/visual_validation/VISUAL_VALIDATION.md` for the 12
source-grounded decisions and `posthoc_adjudication/POSTHOC_REPORT.md` for the
consolidated audit.

# Dataset Integrity Audit

The initial metadata gate found one invalid benchmark item: `spiqa_79`.

- Stored question: `New question:`
- Stored reference: a detailed answer about how alpha affects recommendation
  accuracy for cross-entropy, TOP1-max, and BPR-max losses.
- The same mismatch exists in the upstream local VisDoM CSV and processed
  metadata; it was not introduced by the resumable runner.
- Both the 8B and 32B G2 readers receive the placeholder as the question and
  consequently reason about unrelated retrieved material.

`spiqa_79` must be labeled `dataset_failure` and excluded from valid accuracy
and G2 failure denominators.

The remaining 99 questions passed the same basic integrity gate: nonempty
reference and a non-placeholder question of at least 20 characters.

## Source-grounded visual integrity findings

The later raw-image review found four additional semantic benchmark defects
that a metadata-only gate cannot detect:

- `spiqa_164`: the caption says the overall topology is five hops, while the
  literal question asks about Node 1, which the source identifies as the
  directly Internet-connected border router.
- `spiqa_195`: the reference says both ACGAN losses decrease, but the raw plot
  shows a rising/high-variance orange generator loss and a falling/oscillating
  blue discriminator loss.
- `spiqa_281`: the reference says the norm is inversely related to frequency,
  but the source explicitly describes a hump-shaped Luhn profile that
  down-weights both rare and frequent words.
- `spiqa_452`: the question equates the largest/highest tOF bubble with best
  temporal coherence even though tOF is a lower-is-better metric. ENet is the
  literal largest bubble; TecoGAN has the better low tOF.

These four cases and `spiqa_79` are excluded from the corrected audit. The
source-grounded valid denominator is therefore **95**. See
`visual_validation/VISUAL_VALIDATION.md` for provenance and case decisions.

## Matched 32B result for `spiqa_96`

`spiqa_96` is a valid benchmark item. The matched 32B reader reproduced the 8B
Planning Graph failure for all 15 official attempts. Its `<dag>` block contains
single LaTeX backslashes such as `\(k\)` inside a JSON string, causing Python's
`json.loads()` to raise `Invalid \escape`.

The online `query_llm()` call in `agent_search/pred_kw.py` does not request
`response_format` or a JSON schema; it relies only on prompt-generated `<dag>`
tags and then parses their contents as JSON. Therefore, this failure is an
official-path structured-output integration defect, not merely an incapable 8B
model or an unhealthy server.

# Raw Visual Validation of 12 Disputed SPIQA Cases

## Method

For each case, the exact base64 image bytes stored in the cached Content Graph
were decoded and compared with the original processed-document image. Because
the graph builder JPEG-reencoded the images, provenance was established using
matching dimensions plus a conservative 32×32 difference-hash comparison. All
retrieved images mapped back to source-document images. The question, reference,
8B answer, matched 32B answer, Worker responses, source text and raw image were
then compared. Frozen execution artifacts were not modified.

This is a first expert visual pass. The four rows labeled `dataset_failure`
should receive independent human confirmation before publication.

## Results

| Case | Final status | Raw-evidence conclusion |
|---|---|---|
| `spiqa_116` | `worker_support_failure` | At x=7, the proposed and Yosinski multi-shot curves are both near 71–72%; the proposed method is only marginally higher. The 8B +10-point claim and 32B 75-vs-70 values are unsupported. |
| `spiqa_163` | `no_failure` | The retrieved Hilbert figure shows recursive four-way subdivision and repetition of the connected pattern. The 8B answer substantially matches the vague reference. |
| `spiqa_164` | `dataset_failure` | The caption says the overall topology is five hops, but Node 1 is explicitly the Internet-connected border router. The reference answers the caption, not the literal Node-1-to-Internet question. |
| `spiqa_195` | `dataset_failure` | The ACGAN orange loss rises with large variance while blue falls/oscillates. The reference claim that both decrease contradicts the raw curves; the 32B interpretation is closer to the source. |
| `spiqa_215` | `no_failure` | RGB activations are richer and texture-heavy; depth activations are cleaner silhouettes. The 8B answer describes this same visual contrast. |
| `spiqa_234` | `no_failure` | r-RNTN PPL decreases with K and approaches the fixed RNTN baseline near 128.8. The intended answer is correct, though wording that RNTN itself varies with K is imprecise. |
| `spiqa_235` | `no_failure` | Error decreases with FLOPS and the small adaptive ANN outperforms the large non-adaptive ANN over the relevant range. |
| `spiqa_281` | `dataset_failure` | The source shows a hump: rare and frequent terms are down-weighted and mid-rank terms peak. The reference's globally inverse relationship is false. |
| `spiqa_368` | `worker_support_failure` + parser | The correct MNIST attack curves were retrieved and readable, but Workers said the required evidence was unavailable; final generation then ended without an answer tag. |
| `spiqa_452` | `dataset_failure` | ENet is literally the largest tOF bubble, but lower tOF is better; TecoGAN is smaller and more coherent. The question incorrectly equates largest/highest with best. |
| `spiqa_578` | `retrieval_failure` | Retrieved Table 4 contains model-level NPMI, not topic rows. The required Table 6 top topic (`turks armenian ...`, 0.77) was absent from retrieval. |
| `spiqa_98` | `worker_support_failure` + parser | One-hop goodput decreases; segment loss is tiny and non-monotonic. The 8B full-range “both decrease” claim is unsupported, and its correct raw-output fragment also lacked the closing tag. |

## Corrected audit effect

Visual review changes the provisional audit in three important ways:

1. `spiqa_163` and `spiqa_215` are restored as correct 8B answers.
2. `spiqa_164`, `spiqa_195`, `spiqa_281`, and `spiqa_452` are excluded as
   benchmark question/reference defects.
3. `spiqa_368` moves from retrieval to Worker support, `spiqa_578` moves from
   Worker support to retrieval, and `spiqa_98` moves from parser-only to Worker
   support with parser as a secondary failure.

Together with the previously invalid `spiqa_79`, the corrected valid denominator
is **95**. The optimized-8B configuration has **65/95** semantically correct raw
or parsed answers and **30/95** incorrect/no-answer outcomes. Six of the 65
correct raw answers were still lost by the official final-output parser. The
seventh previously counted recovered answer, `spiqa_98`, was removed after the
raw figure showed that its segment-loss trend was unsupported.

Corrected primary failure phenomena on valid cases:

- `worker_support_failure`: **20**
- `parser_failure`: **9**
- `retrieval_failure`: **4**
- `decomposition_failure`: **2**
- `composition_failure`: **1**

These total **36** phenomena: 30 incorrect/no-answer outcomes plus six correct
raw answers lost by the parser.

## Evidence locations

Every case has an immutable-derived review packet under `cases/<question_id>/`:

- `packet.json` records the question, answers, classification and provenance;
- `nodes/` contains the exact decoded graph images supplied to G²;
- `contact_sheet.jpg` labels cited and retrieved nodes for inspection.

The machine-readable decisions are in `VISUAL_VALIDATION.json`, and the complete
extraction inventory is in `INVENTORY.json`.

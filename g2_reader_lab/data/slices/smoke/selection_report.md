# Selection Report

## Method

- Fixed seed: `20260817`.
- Rows are ranked by `SHA-256(seed:id)` and interleaved by inferred answer type.
- Selection never uses baseline output or model correctness.
- Every listed PDF must exist, contain at least one page, and expose a readable first-page media box.
- Smoke is a deterministic subset of mini: the first three selected rows per dataset.
- Evidence type defaults to the dataset modality and is refined only by explicit words in the question.
- Hop labels remain `unknown` unless a documented lexical compositional marker is present; released metadata has no hop annotation.

## Distribution

```json
{
  "seed": 20260817,
  "selection_algorithm": "SHA-256(seed:id), interleaved by inferred answer type",
  "configuration_hash": "f39841e3b670a312f1c028c7a1097596db2cf77652db3a972f6158e2ba87e75c",
  "question_count": 15,
  "ids": [
    "feta_tab_10447",
    "feta_tab_15959",
    "feta_tab_13469",
    "paper_tab_125",
    "paper_tab_159",
    "paper_tab_209",
    "spiqa_342",
    "spiqa_362",
    "spiqa_590",
    "scgqa_176",
    "scgqa_200",
    "scgqa_189",
    "slidevqa_521",
    "slidevqa_41",
    "slidevqa_342"
  ],
  "dataset_counts": {
    "feta_tab": 3,
    "paper_tab": 3,
    "scigraphqa": 3,
    "slidevqa": 3,
    "spiqa": 3
  },
  "answer_type_counts": {
    "list": 5,
    "number": 4,
    "text": 6
  },
  "evidence_type_counts": {
    "chart/figure": 4,
    "figure": 2,
    "slide": 2,
    "table": 7
  },
  "hop_type_counts": {
    "compositional": 1,
    "unknown": 14
  }
}
```

## Recorded exclusions encountered before quotas were filled

- `scgqa_176`: duplicate stable ID in released metadata
- `scgqa_200`: duplicate stable ID in released metadata
- `scgqa_189`: duplicate stable ID in released metadata
- `scgqa_304`: duplicate stable ID in released metadata
- `scgqa_175`: duplicate stable ID in released metadata
- `scgqa_323`: duplicate stable ID in released metadata
- `scgqa_276`: duplicate stable ID in released metadata
- `scgqa_236`: duplicate stable ID in released metadata
- `scgqa_345`: duplicate stable ID in released metadata
- `scgqa_46`: duplicate stable ID in released metadata
- `scgqa_160`: duplicate stable ID in released metadata
- `scgqa_303`: duplicate stable ID in released metadata
- `scgqa_28`: duplicate stable ID in released metadata
- `scgqa_102`: duplicate stable ID in released metadata
- `scgqa_138`: duplicate stable ID in released metadata
- `scgqa_18`: duplicate stable ID in released metadata
- `scgqa_164`: duplicate stable ID in released metadata
- `scgqa_32`: duplicate stable ID in released metadata
- `scgqa_335`: duplicate stable ID in released metadata

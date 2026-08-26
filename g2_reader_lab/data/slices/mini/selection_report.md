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
  "configuration_hash": "aca6abc8d419d5be06ff32b97acd2cd8ea6f15edd904e3779228b92ca0117cad",
  "question_count": 100,
  "ids": [
    "feta_tab_10447",
    "feta_tab_15959",
    "feta_tab_13469",
    "feta_tab_10429",
    "feta_tab_8114",
    "feta_tab_9274",
    "feta_tab_12844",
    "feta_tab_13649",
    "feta_tab_13210",
    "feta_tab_13695",
    "feta_tab_1525",
    "feta_tab_8010",
    "feta_tab_13241",
    "feta_tab_21409",
    "feta_tab_17798",
    "feta_tab_15050",
    "feta_tab_11420",
    "feta_tab_17981",
    "feta_tab_16388",
    "feta_tab_16622",
    "paper_tab_125",
    "paper_tab_159",
    "paper_tab_209",
    "paper_tab_302",
    "paper_tab_10",
    "paper_tab_227",
    "paper_tab_199",
    "paper_tab_167",
    "paper_tab_195",
    "paper_tab_185",
    "paper_tab_45",
    "paper_tab_226",
    "paper_tab_11",
    "paper_tab_206",
    "paper_tab_127",
    "paper_tab_183",
    "paper_tab_34",
    "paper_tab_26",
    "paper_tab_301",
    "paper_tab_16",
    "spiqa_342",
    "spiqa_362",
    "spiqa_590",
    "spiqa_423",
    "spiqa_346",
    "spiqa_339",
    "spiqa_247",
    "spiqa_564",
    "spiqa_256",
    "spiqa_482",
    "spiqa_200",
    "spiqa_183",
    "spiqa_413",
    "spiqa_303",
    "spiqa_29",
    "spiqa_481",
    "spiqa_385",
    "spiqa_601",
    "spiqa_80",
    "spiqa_275",
    "scgqa_176",
    "scgqa_200",
    "scgqa_189",
    "scgqa_304",
    "scgqa_175",
    "scgqa_323",
    "scgqa_276",
    "scgqa_236",
    "scgqa_345",
    "scgqa_46",
    "scgqa_160",
    "scgqa_303",
    "scgqa_28",
    "scgqa_102",
    "scgqa_138",
    "scgqa_18",
    "scgqa_164",
    "scgqa_32",
    "scgqa_335",
    "scgqa_108",
    "slidevqa_521",
    "slidevqa_41",
    "slidevqa_342",
    "slidevqa_284",
    "slidevqa_522",
    "slidevqa_139",
    "slidevqa_364",
    "slidevqa_14",
    "slidevqa_412",
    "slidevqa_467",
    "slidevqa_411",
    "slidevqa_285",
    "slidevqa_231",
    "slidevqa_7",
    "slidevqa_258",
    "slidevqa_69",
    "slidevqa_338",
    "slidevqa_163",
    "slidevqa_520",
    "slidevqa_283"
  ],
  "dataset_counts": {
    "feta_tab": 20,
    "paper_tab": 20,
    "scigraphqa": 20,
    "slidevqa": 20,
    "spiqa": 20
  },
  "answer_type_counts": {
    "list": 22,
    "number": 16,
    "text": 62
  },
  "evidence_type_counts": {
    "chart/figure": 22,
    "figure": 16,
    "slide": 16,
    "table": 46
  },
  "hop_type_counts": {
    "compositional": 7,
    "unknown": 93
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

# Question-Decomposition Findings Bundle

Last update: 2026-09-23

## Purpose

This folder contains the matched 500-question decompositions from
Qwen2-VL-2B and Qwen3-4B, their blind Qwen3-14B comparison, and a separate
10-question Qwen3-14B thinking-mode test.

## Main finding

Qwen3-4B-Instruct-2507 is a substantially better small-model decomposition
baseline than Qwen2-VL-2B-Instruct under the tested natural-decomposition
prompt.

The blind Qwen3-14B judge produced 499 valid paired judgments:

| Preference | Questions |
|---|---:|
| Qwen3-4B better | 378 |
| Qwen2-VL-2B better | 70 |
| Tie | 51 |

The judge marked 375 Qwen3-4B plans and 78 Qwen2-VL-2B plans as fully
correct. These are provisional model judgments, not human-verified accuracy.
Representative inspection supports the main relative result: 4B usually
produced fewer repeated, irrelevant, or invented tasks. However, it still
over-expanded some simple questions.

Both models generated outputs for all 500 frozen questions. Qwen3-4B reached
the 256-token limit in 23 cases, compared with 68 cases for Qwen2-VL-2B.

## Files

- [QWEN2_VL_2B_500_DECOMPOSITIONS.jsonl](QWEN2_VL_2B_500_DECOMPOSITIONS.jsonl):
  historical 2B outputs for the 500 frozen questions.
- [QWEN3_4B_500_DECOMPOSITIONS.jsonl](QWEN3_4B_500_DECOMPOSITIONS.jsonl):
  matched Qwen3-4B outputs for the same questions and prompt.
- [QWEN2_2B_VS_QWEN3_4B_JUDGMENTS.jsonl](QWEN2_2B_VS_QWEN3_4B_JUDGMENTS.jsonl):
  question-level blind comparisons.
- [QWEN2_2B_VS_QWEN3_4B_SUMMARY.json](QWEN2_2B_VS_QWEN3_4B_SUMMARY.json):
  aggregate comparison metrics.
- [QWEN3_14B_THINKING_10_QUESTIONS.json](QWEN3_14B_THINKING_10_QUESTIONS.json):
  separate 10-question thinking-mode generation test. This is not a
  500-question run and is not the comparison judge output.

## Evaluation distinction

The paired comparison used Qwen3-14B with thinking disabled, temperature zero,
and hidden randomized A/B order. The included thinking-mode file is a separate
smoke experiment. Do not combine the two results.

## Decision

Use Qwen3-4B-Instruct-2507 as the small-model natural-decomposition baseline
for the next O--R experiment. Keep these outputs frozen and perform a matched
human audit before reporting absolute decomposition accuracy.

## Eventual decomposition target

The final objective is to make the model produce an executable O--R plan that
separates requested answer obligations, required evidence, operations, and the
final answer format.

### Sample scientific question

> Which method achieves the highest F1 score on the SciERC dataset in Table 2,
> how much higher is it than DyGIE++, and does Figure 4 show the same method
> ordering?

### Planner output

```yaml
obligations:
  - id: O1
    objective: identify the method with the highest SciERC F1 score

  - id: O2
    objective: calculate its improvement over DyGIE++

  - id: O3
    objective: determine whether Figure 4 shows the same ordering

requirements:
  - id: R1
    supports: [O1, O2]
    evidence_needed: SciERC F1 score for every method
    source_policy: pdf_table
    source_hint: Table 2
    operation: read_column

  - id: R2
    supports: O3
    evidence_needed: method labels and their ordering
    source_policy: pdf_figure
    source_hint: Figure 4
    operation: compare_ordering

operations:
  - id: F1
    supports: O1
    inputs: R1
    function: argmax

  - id: F2
    supports: O2
    inputs:
      - result_of: F1
      - DyGIE++ score from R1
    function: subtract

  - id: F3
    supports: O3
    inputs:
      - result_of: F1
      - result_of: R2
    function: equality_compare

answer_format:
  - best_method
  - improvement_over_DyGIE++
  - figure_table_agreement
```

The planner preserves all three requested parts without adding background
questions or answering them.

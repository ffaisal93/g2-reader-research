# Matched 32B Reader Replay Adjudication

The Content Graph is held fixed to the optimized-8B graph. Only the
online reader changes from Qwen3-VL-8B to Qwen3-VL-32B, so these
comparisons isolate reader/model sensitivity; they do not measure graph
construction quality or an end-to-end original-32B baseline.

- Replay targets: **11**
- Completed semantic adjudications: **11**
- Official parser successes: **11/11**
- Semantically correct raw/candidate answers: **5/11**
- 8B incorrect to 32B correct: **4**
- 8B correct to 32B incorrect: **0**

| Question | 8B category | 8B verdict | 32B parsed | 32B semantic | Time (s) |
|---|---|---|---:|---|---:|
| `spiqa_39` | `parser_failure` | `correct` | yes | `correct` | 277.18 |
| `spiqa_4` | `worker_support_failure` | `incorrect` | yes | `correct` | 85.05 |
| `spiqa_110` | `worker_support_failure` | `incorrect` | yes | `incorrect` | 113.61 |
| `spiqa_116` | `worker_support_failure` | `incorrect` | yes | `correct` | 96.07 |
| `spiqa_522` | `worker_support_failure` | `incorrect` | yes | `incorrect` | 92.43 |
| `spiqa_163` | `retrieval_failure` | `incorrect` | yes | `correct` | 110.33 |
| `spiqa_195` | `retrieval_failure` | `incorrect` | yes | `incorrect` | 90.66 |
| `spiqa_396` | `retrieval_failure` | `incorrect` | yes | `correct` | 120.07 |
| `spiqa_44` | `decomposition_failure` | `incorrect` | yes | `incorrect` | 168.82 |
| `spiqa_571` | `decomposition_failure` | `incorrect` | yes | `incorrect` | 452.45 |
| `spiqa_47` | `composition_failure` | `incorrect` | yes | `incorrect` | 177.27 |

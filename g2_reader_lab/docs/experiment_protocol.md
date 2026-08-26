# Controlled experiment protocol

## Frozen inputs

- Seed: `20260817`.
- Smoke: 15 questions, three from each of FetaTab, PaperTab, SPIQA, SciGraphQA, and SlideVQA.
- Mini: 100 questions, twenty from each subset.
- Processed source: Hugging Face revision `57d76a6ab4872592dfe47dbf4fae6cd77bcf184b`.
- The 109 smoke documents validate offline against pinned metadata: 109 valid, zero failed, 764,654,068 bytes.

## Shared model budget

Both systems use `/mnt/maxtox-nfs-student/zff/models/qwen2.5-vl-7b` in BF16 and `/mnt/maxtox-nfs-student/zff/models/bge-m3`, served from one local OpenAI-compatible endpoint. Concurrency is one. Development context is 8,192 tokens and generation is capped at 1,024 tokens. Evolution and refinement are bounded to three rounds.

The available 32B checkpoint is text-only, not Qwen3-VL-32B-Instruct. This work evaluates architecture under a shared 7B multimodal backbone and does not claim reproduction of headline paper scores.

## Run levels

1. Unit tests validate deterministic graph/parser semantics.
2. Model smokes validate CUDA, text/image generation, and embedding.
3. One-question capped plumbing validates complete external interfaces. Caps belong in result names and cache keys.
4. Formal scoring requires identical IDs, all referenced documents, matching budgets, and no `--max-nodes` plumbing cap.

Report exact match, normalized containment, wall latency, call counts, and structured-output fallbacks. Never compare accuracy produced with different document/node caps. Retain JSONL predictions plus JSON and Markdown traces.

# Qwen3-VL JSON validation for official G²-Reader

Date: 2026-08-20

## Decision

`Qwen/Qwen3-VL-32B-Instruct-FP8` served by vLLM 0.27.1 eliminated the
malformed-JSON failure class observed in `memory_systems_pilot_v4` for the
tested workload. The old `qwen2.5-vl-7b` checkpoint was deleted only after all
gates below passed.

## Runtime

- GPU: NVIDIA L40S, 46 GB
- Chat/VLM model: `/mnt/maxtox-nfs-student/zff/models/qwen3-vl-32b-instruct-fp8`
- Chat endpoint: `http://127.0.0.1:18000/v1`
- Served model name: `local-qwen-vl`
- Embedding endpoint: `http://127.0.0.1:18001/v1`
- Embedding model: local BGE-M3 on CPU
- vLLM maximum model length: 24,000 tokens
- KV-cache dtype: BF16
- Official implementation exercised: `baseline_original/G2_Reader_patched`

The 24,000-token limit was selected because the 32,768-token BF16 KV cache did
not fit alongside the 33.08-GiB FP8 checkpoint on one L40S. No FP8 KV-cache
quantization was used.

## Validation gates

### 1. Protocol-level structured output

All of the following returned JSON that Python parsed successfully:

- `response_format={"type":"json_object"}` with LaTeX/backslash-heavy text
- strict `json_schema`
- adversarial strings containing LaTeX commands and a Windows path

Result: 3/3 passed.

### 2. Replay of every prior malformed response

The content from all 24 `failed_response_*.txt` files in
`memory_systems_pilot_v4/_debug_logs` was replayed through the new endpoint
using the official JSON-object response format.

- Valid JSON: 24/24
- Correct top-level key/type shape: 24/24
- Length-truncated responses: 0/24
- Wall time: 174.115 seconds

Machine-readable result:
`results/official_trace/audits/qwen3_vllm_json_validation.json`

### 3. Real official G² prebuild

The official `prebuild.amem_new.construct_memory()` path processed one actual
SPIQA paper (`1708.00160v2`) with no replacement analysis logic:

- Text analyses: 24/24 successful
- Image analyses: 15/15 successful
- Text embeddings: 24/24 successful
- Image embeddings: 15/15 successful
- Saved memory nodes: 39
- Saved content-graph edges: 150
- Nodes containing the failure fallback summary: 0
- New malformed-response debug files: 0

Artifacts:

- `results/official_trace/audits/qwen3_prebuild_gate_v1/console.log`
- `results/official_trace/memory_systems_qwen3_prebuild_gate_v1/spiqa_spiqa_342_docs_1_iter_0/content_graph.json`
- `results/official_trace/memory_systems_qwen3_prebuild_gate_v1/spiqa_spiqa_342_docs_1_iter_0/memories.pkl`
- `results/official_trace/memory_systems_qwen3_prebuild_gate_v1/spiqa_spiqa_342_docs_1_iter_0/retriever_embeddings.npy`

## Separate dataset-plumbing defect discovered

The official helper strips the dataset prefix from `spiqa_342` before comparing
it with a CSV column whose values still contain that prefix. The normal runner
therefore suppresses the resulting exception and continues with zero retrieved
text and zero images. For this validation only, `spiqa_spiqa_342` was supplied;
after the helper's single prefix removal it resolves the intended CSV row. This
workaround does not change content analysis, graph construction, embedding, or
the model prompts. The initial empty-evidence inference run is invalid as a RAG
quality measurement and is not counted above.

## Conditional cleanup

After the three gates passed, exactly this directory was deleted:

`/mnt/maxtox-nfs-student/zff/models/qwen2.5-vl-7b`

It occupied approximately 16 GB and is no longer present. The shared NFS
filesystem's `df` available-space figure did not update immediately; no process
holds a deleted file from that path open.

## Scope of the conclusion

These results establish that the tested malformed-JSON failure class is gone
for the prior 24 failures and for a fresh 39-node official prebuild. They do not
yet establish benchmark answer accuracy or guarantee zero malformed output for
every possible future input.

# G²-Reader Reproduction Lab

This workspace reproduces the released G²-Reader pipeline, records the minimum blocker repairs needed to execute it, and implements an independently structured minimal baseline for controlled comparison. The governing contract is [`../resources/implementation.md`](../resources/implementation.md).

For a detailed code-grounded explanation of both runtime paths, see [`docs/g2_and_minimal_g2_architecture_walkthrough.md`](docs/g2_and_minimal_g2_architecture_walkthrough.md).

For the authoritative cross-experiment conclusions, corrected failure counts,
failure-term definitions, and source-grounded examples, see
[`experiments/FINDINGS.md`](experiments/FINDINGS.md).

## Progress

- [x] Phase 1 — system inspection and isolated environment
  - [x] Host hardware and software inspected
  - [x] Isolated environment created at `.venv`
  - [x] Minimal dependency set pinned
  - [x] CUDA PyTorch tensor smoke test passed
  - [x] VLM and embedding-model smoke tests passed
- [x] Phase 2 — repositories and processed data pinned
  - [x] G²-Reader pinned at `e4d047a756ef9136ea7f0c4dd8ba36eb1b08ec27`
  - [x] VisDoM pinned at `2d809ac87360d54b0765e9be1cab75808d37642a`
  - [x] Processed dataset metadata acquired, hashed, selectively downloaded, and validated
- [x] Phase 3 — deterministic smoke and mini slices
- [x] Phase 4 — released-code audit
- [x] Phase 5 — corrected released-code baseline
- [x] Phase 6 — clean minimal implementation
- [ ] Phase 7 — controlled comparison
- [ ] Phase 8 — research documentation and completion audit
  - Status: [`docs/completion_audit.md`](docs/completion_audit.md)

## Environment

```bash
source .venv/bin/activate
python environment/gpu_smoke_test.py --output results/smoke/gpu_smoke.json
```

The current host has a Tesla V100-PCIE-32GB (compute capability 7.0). The CUDA toolkit is not installed; PyTorch uses its pinned CUDA 12.6 runtime wheel. Python 3.12 is used because no Python 3.10 or 3.11 interpreter was available on the host. See [`environment/system_report.md`](environment/system_report.md) and [`environment/environment.lock.yml`](environment/environment.lock.yml).

## Troubleshooting log

### 2026-08-17: restricted sandbox failed to initialize loopback

Several initial read-only commands failed before execution with:

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

The commands were rerun with explicit approval outside that broken sandbox. No project data was changed by the failed attempts.

### 2026-08-17: no system CUDA compiler

`nvcc --version` returned `nvcc: command not found`. This is not a PyTorch blocker: the installed driver supports the pinned CUDA runtime bundled by the official PyTorch wheel.

### 2026-08-17: selective processed-data download

The 109 documents referenced by the smoke slice were estimated before download. Offline validation against the pinned Hugging Face metadata confirms all 109 documents, zero failures, and exactly 764,654,068 payload bytes. No API-key directory was read.

### 2026-08-18: controlled local model profile

Both implementations use the existing NFS checkpoints `qwen2.5-vl-7b` and `bge-m3` through one local endpoint. BF16 is required: the VLM image smoke returned `Red` in 6.15 seconds at 16.61 GB peak VRAM; BGE produced a normalized 1,024-dimensional vector in 3.59 seconds at 2.28 GB peak. Formal comparison status is documented in `docs/comparison_report.md`.

### 2026-08-18: local endpoint memory and structured-output limits

The first upstream attempts failed when long multimodal prompts exhausted VRAM and when the 7B model produced truncated or schema-invalid Planning Graph JSON. The final shared service envelope is SDPA/BF16, 20,000 input characters with head-tail truncation, 262,144 image pixels, 1,024 output tokens, expandable CUDA segments, and per-request cache cleanup. Planning JSON remains strictly validated; three invalid attempts produce an explicit single-node fallback.

### 2026-08-18: formal smoke resource gate

The complete 15-question smoke slice contains 5,804 coarse Content Graph nodes. Three evolution rounds require at least 23,216 VLM calls and as many as 69,648 structured attempts before online planning. This exceeds a one-night V100 budget, so only the matched one-document end-to-end comparison was executed; `results/smoke/full_run_cost_estimate.json` is the concrete gate. No full-smoke accuracy claim is made.

# Implementation Plan: Reproduce and Simplify G²-Reader

## Instruction to Codex

Treat this document as the implementation contract for the first phase of the project. Work autonomously through the phases below, but do not skip validation steps or silently change the baseline architecture.

The immediate objective is **not** to add our proposed modular reasoning layer. First establish a reproducible G²-Reader baseline and build a small, readable implementation that exposes every important operation. Later work will add capability modules and compare them against this minimal baseline.

## Primary objectives

1. Inspect the host system and create an appropriate isolated Python environment. The machine is expected to have a GPU with approximately 32 GB of VRAM, but detect the actual hardware and software rather than assuming a CUDA version.
2. Clone and pin the official G²-Reader implementation and the exact data artifacts needed for its VisDoMBench evaluation.
3. Construct deterministic, substantially smaller benchmark slices for fast development and initial evaluation.
4. Audit the entire released G²-Reader code path and document what the code actually executes, including discrepancies from the paper.
5. Preserve the official repository as a read-only reference. Apply only documented blocker fixes in a separate baseline worktree or copy.
6. In a separate folder, implement a clean and minimal G²-Reader that is easy to read, trace, test, and modify.
7. Run the corrected released baseline and the minimal implementation on identical benchmark slices, using identical model, retrieval, and evaluation budgets wherever possible.

## Non-goals for this phase

- Do not implement scientific, table, chart, slide, database, or other plug-in reasoning modules yet.
- Do not introduce a fine-grained scientific ontology yet.
- Do not optimize benchmark scores by changing prompts, adding tools, or tuning separately for individual datasets.
- Do not claim reproduction of the paper's headline results from a small benchmark slice.
- Do not silently repair or reinterpret the original implementation. Every baseline correction must be recorded.
- Do not download all upstream raw benchmark corpora when the exact processed VisDoMBench/G²-Reader artifacts are sufficient.

## Required project layout

Create the following structure under the current workspace:

```text
g2_reader_lab/
├── README.md
├── environment/
│   ├── system_report.md
│   ├── environment.lock.yml
│   └── gpu_smoke_test.py
├── external/
│   ├── G2_Reader/                 # pristine pinned upstream checkout
│   └── VisDoM/                    # pristine pinned benchmark checkout
├── data/
│   ├── metadata/                  # processed JSONL metadata
│   ├── documents/                 # only documents needed by selected slices
│   ├── slices/
│   │   ├── smoke/
│   │   └── mini/
│   └── manifests/
├── baseline_original/
│   ├── G2_Reader_patched/         # separate worktree/copy for blocker fixes
│   ├── patches/
│   ├── configs/
│   └── scripts/
├── minimal_g2_reader/
│   ├── README.md
│   ├── pyproject.toml
│   ├── configs/
│   ├── src/minig2/
│   ├── scripts/
│   └── tests/
├── docs/
│   ├── upstream_code_walkthrough.md
│   ├── paper_vs_code.md
│   ├── baseline_repairs.md
│   ├── minimal_architecture.md
│   └── experiment_protocol.md
└── results/
    ├── smoke/
    ├── mini/
    └── comparisons/
```

Do not place generated model files, document corpora, virtual environments, caches, or large result artifacts under Git version control. Create a suitable `.gitignore`.

---

## Phase 1: Inspect the system before installing anything

Create `environment/system_report.md` containing:

- operating system and version;
- CPU model and core count;
- system RAM;
- GPU model, VRAM, driver version, and compute capability where available;
- output of `nvidia-smi` when available;
- installed CUDA toolkit version, if any;
- Python versions currently available;
- free disk space;
- whether `uv`, Conda/Mamba, Docker, Git LFS, and Hugging Face CLI are installed;
- whether outbound access to GitHub and Hugging Face works.

Use read-only detection commands. Do not assume that the CUDA toolkit version must match the version displayed by `nvidia-smi`; select PyTorch using the installed driver compatibility and an officially supported wheel.

### Environment decision

Prefer the following order:

1. `uv` with Python 3.10 or 3.11;
2. `python -m venv` with Python 3.10 or 3.11;
3. Conda/Mamba only when required by CUDA or MinerU compatibility.

Create one project environment at:

```text
g2_reader_lab/.venv
```

Do not install the upstream `requirements.txt` blindly. It mixes a very large number of packages and includes both CUDA 11 and CUDA 12 runtime families. Instead:

1. determine the imports actually needed by the released inference and preprocessing paths;
2. create a minimal dependency specification;
3. install one compatible PyTorch/CUDA stack;
4. add dependencies incrementally;
5. produce `environment/environment.lock.yml` with exact versions and installation commands.

### GPU strategy

Run a GPU smoke test before model installation and record peak allocated VRAM.

Use two model profiles:

- **Development profile:** a smaller compatible local vision-language model that comfortably fits in 32 GB VRAM and allows repeated testing. Prefer the closest Qwen-VL family model supported by the released prompts and serving stack.
- **Paper-comparison profile:** Qwen3-VL-32B-Instruct only if a supported quantized checkpoint and inference backend fit safely in the detected hardware. Do not promise that a 32B multimodal model will fit merely because weights fit; account for KV cache, image tokens, and long contexts.

If the 32B model does not fit reliably, use the same smaller model for every compared method and state clearly that the experiment tests architectural improvement under a controlled backbone, not exact reproduction of the paper's model scale.

Support OpenAI-compatible local endpoints where practical so the original and minimal implementations can call the same model server. Keep model identifiers, quantization, maximum context length, image limits, and decoding settings in versioned YAML configuration rather than source code.

Acceptance checks:

- PyTorch detects the GPU.
- A small tensor operation runs on the GPU.
- The selected VLM processes one text-and-image prompt.
- The embedding model produces one vector.
- Peak VRAM and latency are recorded.

---

## Phase 2: Clone and pin repositories and datasets

Clone the following repositories into `g2_reader_lab/external/`:

```text
https://github.com/DorothyDUUU/G2_Reader.git
https://github.com/MananSuri27/VisDoM.git
```

The G²-Reader version previously audited was:

```text
e4d047a756ef9136ea7f0c4dd8ba36eb1b08ec27
```

Default to that commit for reproducibility unless the user explicitly chooses a newer version. If a newer upstream commit exists, record it but do not silently substitute it.

Obtain the processed G²-Reader data artifacts from:

```text
https://huggingface.co/datasets/LittleWhite1031/G2-Reader
```

Record the exact Git commit or Hugging Face snapshot revision for every external artifact in:

```text
g2_reader_lab/data/manifests/source_revisions.json
```

Include:

- repository URL;
- resolved commit SHA or dataset snapshot revision;
- retrieval date;
- license information;
- local path;
- hashes for processed JSONL files;
- any files unavailable or requiring authentication.

### Data-download policy

The initial experiment uses the five VisDoMBench subsets evaluated by G²-Reader:

- FetaTab;
- PaperTab;
- SPIQA;
- SciGraphQA;
- SlideVQA.

First obtain only metadata/JSONL files. Select sample IDs before downloading document payloads. Then download or materialize only the documents referenced by the selected samples. If Hugging Face does not support efficient selective download for the artifact layout, document the limitation before downloading a large snapshot.

Do not mix independently reprocessed upstream benchmarks with the G²-Reader processed version in the primary comparison. Exact preprocessing compatibility matters.

---

## Phase 3: Create deterministic benchmark slices

Create two slices with a fixed seed of `20260817`:

### Smoke slice

- 3 examples from each of the five subsets;
- 15 questions total;
- intended only for installation, parsing, retrieval, and end-to-end debugging.

### Mini slice

- 20 examples from each of the five subsets;
- 100 questions total;
- intended for initial accuracy, latency, token, and ablation comparisons.

If a dataset has fewer usable examples after document validation, include all usable examples and record the shortfall.

Selection must be deterministic and performed by stable sample ID. Where metadata permits, balance the mini slice across:

- answer type: text, number, list;
- evidence type: text, table, chart/figure, slide;
- single-hop versus compositional questions;
- number of documents;
- presence of explicit figure/table references.

Do not use model correctness or baseline output to choose examples.

For every slice, save:

```text
questions.jsonl
manifest.json
document_manifest.json
selection_report.md
```

Each question record must preserve the original benchmark ID, dataset, question, answer, document list, main document, and any available evidence annotations. `selection_report.md` must describe the sampling rules and distribution.

Validate that every referenced document exists and can be parsed before freezing the slice. Never replace a failed example without recording the original ID and reason for exclusion.

---

## Phase 4: Audit the released G²-Reader implementation

Read every Python file, shell script, prompt, configuration file, README section, dataset wrapper, and evaluation script in the pinned repository.

Create `docs/upstream_code_walkthrough.md` organized by the actual runtime path:

```text
dataset row
→ document resolution
→ MinerU parsing
→ text/image node creation
→ VLM summaries and keywords
→ embeddings
→ initial links
→ graph evolution
→ query retrieval
→ DAG decomposition
→ per-node retrieval and Worker inference
→ evidence checking
→ DAG refinement
→ final reasoning
→ answer extraction and evaluation
```

For every stage, document:

- source files and functions;
- inputs and outputs;
- persisted artifacts;
- model calls and prompts;
- graph state before and after the stage;
- concurrency behavior;
- error handling and fallbacks;
- configurable versus hard-coded values;
- whether the behavior matches the paper.

Create a separate `docs/paper_vs_code.md`. Verify rather than merely repeat the following suspected issues:

1. `_call_llm_evolve()` and its caller appear to disagree about a `max_tokens` argument, potentially causing graph evolution to fail and silently return the original node.
2. The DAG is serialized with parent-to-child edges, while parent execution attempts to consume child results. Verify whether Kahn ordering executes dependencies in the wrong direction.
3. The released JSONL rows do not appear to contain `judge`, while the DAG inference path accesses `item['judge']`.
4. Generation prompts use `<output>`, while the released evaluator appears to extract `<answer>`.
5. Initial reading-order links appear to be created only for text nodes, not for figure/table nodes.
6. Prompts are truncated to approximately 4,096 tokens by retaining the beginning and end, potentially discarding central evidence.
7. The code calls a phrase/regex keyword scorer “BM25”; verify whether a real BM25 implementation is used anywhere.
8. The DAG validator receives a maximum depth but may not enforce it.
9. Replanning appears to execute the whole revised DAG and retain only the final round for answer synthesis rather than reusing verified unchanged nodes.
10. The retrieved graph neighborhood appears to be flattened into `Related Memory` strings and images before generation; verify whether explicit nodes and edges ever reach the Worker or Reasoner.
11. Check whether the supplied shell scripts, module paths, model imports, and evaluation commands run as documented.

Classify every finding as:

- confirmed defect;
- paper/code discrepancy;
- ambiguous behavior requiring an experiment;
- reproducibility limitation;
- stylistic or maintainability issue only.

Do not treat a code defect as a research contribution.

---

## Phase 5: Establish a corrected released-code baseline

Keep `external/G2_Reader` pristine at its pinned commit. Create a separate worktree or copy at:

```text
baseline_original/G2_Reader_patched
```

Apply only fixes required to make the released pipeline execute as intended. Examples include output-tag mismatches, missing optional fields, invalid launch paths, incompatible function signatures, and dependency-order defects.

For every correction:

1. create a minimal failing test or reproduction command;
2. record the original behavior;
3. apply the smallest possible correction;
4. record the corrected behavior;
5. save the patch under `baseline_original/patches/`;
6. explain whether the correction follows the paper or changes the architecture.

Create `docs/baseline_repairs.md` with a table containing:

```text
ID | severity | file/function | observed failure | minimal repair | architectural effect
```

The corrected baseline must expose a complete trace for every question:

- initial retrieved node IDs;
- initial Content Graph neighbors;
- initial Planning Graph JSON;
- execution order;
- evidence retrieved for each planning node;
- intermediate answers;
- sufficiency decision and gaps;
- every revised Planning Graph;
- final evidence and final answer;
- model calls, tokens, latency, and peak VRAM.

Run the corrected baseline on the smoke slice before beginning the clean implementation.

---

## Phase 6: Build the clean minimal implementation

Implement this independently under `minimal_g2_reader/`. It should be small enough that a researcher can understand the complete inference path in one sitting.

Do not copy the upstream file structure or carry over its global variables, hard-coded paths, multiprocessing design, silent exception handling, or mixed-language logging.

### Required module structure

```text
minimal_g2_reader/src/minig2/
├── config.py
├── types.py
├── llm.py
├── embeddings.py
├── parsing.py
├── content_graph.py
├── retrieval.py
├── planning_graph.py
├── agents.py
├── pipeline.py
├── evaluation.py
├── tracing.py
└── cli.py
```

Each file should have one clear responsibility.

### Explicit data types

Use typed dataclasses or Pydantic models for at least:

```text
SourceLocation
ContentNode
ContentEdge
ContentGraph
PlanningNode
PlanningEdge
PlanningGraph
RetrievedEvidence
IntermediateAnswer
EvidenceCheck
ExecutionTrace
FinalAnswer
```

The minimal baseline should retain G²-Reader's coarse evidence units: text chunks and whole table/figure elements. Do not add our future scientific schema yet. Source locations and IDs may be stored for observability, but must not be used to provide extra facts unavailable to the corrected baseline.

### Content Graph implementation

Implement and expose these stages separately:

1. parse ordered multimodal document elements;
2. create text and visual nodes;
3. generate node summary, keywords, and tags;
4. embed summary plus keywords;
5. create initial reading-order/document-native links;
6. construct candidate neighborhoods from current neighbors plus semantic Top-K;
7. invoke graph evolution to update summaries, keywords, and links;
8. re-embed updated nodes;
9. freeze and serialize the graph.

Make evolution rounds, reading-order window, semantic candidate count, maximum links, and concurrency configurable. Default to the paper's intended values where specified, including three evolution rounds, but document every place where the released code behaves differently.

Edges must at least preserve source and target IDs. If a generic relation label is returned by the VLM, retain it for inspection, but do not invent scientific relation types in this phase.

### Structured graph retrieval

Implement the paper's readout transparently:

1. embed the query or subquestion;
2. rank Content Graph nodes by cosine similarity;
3. select the next highest-ranked unseen node;
4. add its immediate neighbors;
5. stop when the node budget is reached;
6. return both the selected node set and induced edges.

Define and test what happens when neighbor expansion exceeds the budget. Preserve scores and selection reasons in the trace.

For architecture-faithful generation, serialize the same raw evidence that the released Worker receives. Also retain the explicit subgraph in the trace, but do not give the minimal model additional graph facts in the primary comparison unless the corrected baseline receives the same information.

### Planning Graph implementation

Implement:

1. probing retrieval;
2. initial DAG decomposition;
3. strict schema parsing;
4. validation of unique IDs, existing edge endpoints, acyclicity, maximum nodes, and maximum depth;
5. a clearly defined dependency direction;
6. dependency-correct execution order;
7. local Content Graph retrieval for each planning node;
8. Worker inference;
9. evidence sufficiency checking;
10. bounded DAG refinement;
11. final synthesis.

Write the edge-direction convention in `minimal_architecture.md` and test it. If a parent answer depends on child answers, execute children before the parent or encode the edges accordingly.

To remain faithful to G²-Reader, the checker in this phase may remain VLM-based. Clearly label its decisions as model judgments rather than deterministic verification.

Do not implement incremental node caching or selective re-execution as an improvement yet. You may record enough state to enable it later.

### Configuration and observability

No model name, API URL, API key, data path, graph parameter, token budget, or concurrency setting may be hard-coded in library code.

Provide:

```text
configs/dev.yaml
configs/paper_faithful.yaml
configs/cpu_test.yaml
```

Every run must produce a machine-readable trace and a compact human-readable trace. The human-readable trace should allow inspection of one example without opening source code.

### Required tests

At minimum, implement:

- parser preserves document and element order;
- node IDs and source locations are stable;
- graph evolution performs an actual model call and does not silently fail;
- graph serialization round-trips;
- neighbor expansion returns the expected nodes and edges;
- retrieval budget behavior is deterministic;
- DAG validator rejects cycles, missing nodes, duplicate IDs, excess depth, and excess node count;
- DAG execution respects dependency direction;
- Worker receives the expected evidence and prerequisite answers;
- evidence-check failure triggers bounded refinement;
- refinement terminates at its configured limit;
- final answer extraction accepts the configured output schema;
- token truncation is explicit and logged;
- one mocked end-to-end question runs without network or GPU access;
- one real smoke question runs through the configured local model.

Use fixtures and mock model clients for unit tests. Do not require expensive VLM calls for the normal test suite.

---

## Phase 7: Controlled initial comparison

Run both systems on identical inputs:

```text
A. corrected released G²-Reader
B. clean minimal G²-Reader
```

Hold constant:

- VLM and embedding model;
- quantization;
- prompts, unless a syntax correction is required and documented;
- document parser and processed data;
- number of documents per question;
- Content Graph evolution rounds;
- retrieval node budget;
- Planning Graph refinement limit;
- decoding temperature and maximum output tokens;
- evaluator;
- hardware.

Run in this order:

1. one hand-inspected example from each dataset;
2. the 15-question smoke slice;
3. the 100-question mini slice only after smoke traces are valid.

### Evaluation

Report:

- native final-answer accuracy using a compatible version of the released evaluator;
- normalized exact match for short and numerical answers where applicable;
- answer extraction failures;
- retrieval failures;
- parser failures;
- invalid Planning Graph rate;
- average refinement rounds;
- average Content Graph nodes and edges;
- average evidence nodes retrieved per planning node;
- VLM and embedding calls;
- input/output tokens;
- wall time;
- peak GPU memory;
- failure count.

The LLM judge must evaluate only the final answer against the gold answer. Do not provide it with internal traces or method identity. Cache judge outputs and manually inspect at least ten disagreements between exact matching and the LLM judge.

Create:

```text
results/comparisons/smoke_comparison.md
results/comparisons/mini_comparison.md
results/comparisons/per_question.jsonl
```

The goal is not for the minimal implementation to outperform the corrected baseline. It should approximately preserve its behavior while being easier to understand and modify. Investigate substantial differences through per-question traces before tuning anything.

---

## Phase 8: Documentation for iterative research

The minimal implementation's README must contain:

1. a ten-minute setup path;
2. one command to build a Content Graph;
3. one command to visualize or print it;
4. one command to execute one question;
5. one command to run the smoke slice;
6. a worked example showing every graph and agent step;
7. a mapping from each paper concept to its source module;
8. known deviations from the released implementation;
9. extension points reserved for future capability modules.

Create `docs/minimal_architecture.md` with the following high-level flow:

```text
OFFLINE
documents
→ parser
→ coarse multimodal nodes
→ summaries/keywords
→ initial links
→ graph evolution
→ frozen Content Graph

ONLINE
question
→ probing retrieval
→ Planning Graph
→ dependency-ordered subquestions
→ local Content subgraphs
→ Worker answers
→ sufficiency check
→ bounded refinement
→ final Reasoner
→ answer
```

At the end, add a section titled `Future modular extension points`, but include interfaces only—not implementations. Reserve places for:

- table-relational execution;
- scientific semantic interpretation;
- chart/figure interpretation;
- cross-page/slide alignment;
- numerical verification;
- evidence ledger and provenance-constrained generation.

The future modules should eventually consume a Planning Node plus retrieved Content subgraph and return a structured, source-grounded result. Do not activate that path in the baseline.

---

## Required progress discipline

- Complete phases in order.
- After each phase, update a checklist in `g2_reader_lab/README.md`.
- Preserve failed commands and their errors in a troubleshooting section; do not hide them.
- Before a large model or dataset download, estimate size and available disk space.
- Before a run estimated to exceed one GPU-hour, execute the same path on one question first.
- Never continue a benchmark run when output extraction, tracing, or evaluation is known to be broken.
- Do not overwrite prior results. Give every run a unique configuration hash and timestamp.
- Store the Git commit and complete resolved configuration in every result directory.
- Ask the user only when credentials, restricted data, a major download, or an architectural choice genuinely blocks progress.

## Definition of done

This phase is complete only when all of the following are true:

- [ ] The environment is reproducible from a lock file.
- [ ] GPU, VLM, and embedding smoke tests pass.
- [ ] External repositories and data revisions are pinned.
- [ ] The smoke and mini slices are deterministic and document-complete.
- [ ] The complete upstream runtime path is documented.
- [ ] Paper/code discrepancies are verified with source locations or tests.
- [ ] The pristine upstream checkout remains unchanged.
- [ ] Every blocker-only baseline repair is recorded as a patch.
- [ ] The corrected released baseline runs on all smoke questions.
- [ ] The clean minimal implementation passes its unit tests.
- [ ] One example from every dataset has an inspectable end-to-end trace.
- [ ] The minimal implementation runs on the smoke slice.
- [ ] The corrected and minimal implementations run under matched budgets.
- [ ] The mini comparison is completed or a concrete resource limitation is documented.
- [ ] No future modular reasoning capability has been silently added to the baseline.
- [ ] The code and documentation make the next modular experiment possible without another rewrite.


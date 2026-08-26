# G²-Reader and Minimal G²-Reader: an end-to-end architecture walkthrough

This document explains what the project is building, why it contains two implementations, how a document becomes a graph, how a question moves through the system, what every major component does, and what the real executions have revealed.

It describes the code as it exists in `/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab` on 2026-08-18. It distinguishes intended architecture from current implementation behavior and from behavior repaired in the corrected upstream worktree.

## 1. What this project is trying to establish

G²-Reader is a multimodal retrieval-and-reasoning architecture for questions over long collections containing text, tables, figures, charts, and slides. Its central idea is to use two different graphs:

1. A persistent **Content Graph** represents the source documents.
2. A question-specific **Planning Graph** represents the reasoning tasks needed to answer one question.

The project has two implementations because they serve different purposes:

| Implementation | Purpose | Location |
|---|---|---|
| Pristine released G²-Reader | Read-only evidence of what upstream published | `external/G2_Reader/` |
| Corrected released baseline | Upstream code with documented blocker and correctness repairs | `baseline_original/G2_Reader_patched/` |
| Minimal G²-Reader | Small, typed, testable implementation that exposes the architecture clearly | `minimal_g2_reader/` |

The corrected baseline answers: “Can the released architecture run after minimal repairs?” The minimal implementation answers: “Can the same main ideas be expressed clearly enough to inspect, test, and extend?” It is not intended to outperform upstream yet.

## 2. The whole system in one picture

```text
                              OFFLINE / REUSABLE

processed MinerU document
        │
        ▼
ordered text, table, figure, and slide elements
        │
        ▼
coarse text chunks + whole visual elements
        │
        ▼
VLM summary / keywords / tags ──────► embedding model
        │                                  │
        └──────────────────┬───────────────┘
                           ▼
               reading-order Content Graph
                           │
                           ▼
          neighborhood-aware graph evolution
                           │
                           ▼
                 frozen, serialized graph


                              ONLINE / PER QUESTION

question ──► embedding ──► probing Content Graph retrieval
                                  │
                                  ▼
                            Planner / DAG
                                  │
                                  ▼
                       validated Planning Graph
                                  │
                                  ▼
                    dependency-correct task order
                                  │
                ┌─────────────────┴─────────────────┐
                ▼                                   ▼
      local graph retrieval                  prerequisite answers
                │                                   │
                └─────────────────┬─────────────────┘
                                  ▼
                               Worker
                                  │
                                  ▼
                         evidence sufficiency check
                            │ sufficient   │ gaps
                            ▼              ▼
                       final Reasoner   bounded replanning
                            │              │
                            └──────┬───────┘
                                   ▼
                           extracted final answer
                                   │
                                   ▼
                       evaluation + complete trace
```

“Offline” means question-independent work that should ideally be reused. In the released implementation the cache is nevertheless scoped by question ID and document selection, so reuse is more limited than the conceptual architecture suggests.

## 3. The two graphs

### 3.1 Content Graph

A Content Graph node is a coarse evidence unit. It is not a scientific entity and it is not a reasoning step.

Typical nodes are:

- a text chunk of roughly 3,000 characters;
- one whole table image;
- one whole figure or chart image;
- one slide image.

Each node contains or is associated with:

- raw text or an image payload;
- document and element position;
- a VLM-generated summary;
- keywords and tags;
- an embedding vector;
- links to nearby or model-related nodes.

The graph supports retrieval. The model does not execute graph algorithms over a scientific ontology. It uses embeddings to find seed nodes, expands into graph neighbors, and then serializes the selected evidence for generation.

### 3.2 Planning Graph

A Planning Graph is generated for one question. Its nodes are subquestions or tasks, not document elements.

This project uses the convention:

```text
parent -> child  means  parent depends on child
```

Therefore the child must execute first. For example:

```text
answer_question -> count_1979_rows
answer_question -> identify_relevant_table
```

The correct execution order begins with `count_1979_rows` and `identify_relevant_table`, then executes `answer_question` with those results available.

This convention matters because the released code originally used a normal parent-first topological order even though parent prompts consumed child answers. The corrected baseline reverses that order. The minimal implementation encodes the dependency-first order directly in `planning_graph.execution_order()`.

## 4. Shared inputs and model service

### 4.1 Benchmark rows

Each frozen JSONL question preserves:

- stable question ID and dataset;
- question and reference answer;
- ordered document list;
- main document;
- available evidence/sampling metadata.

The five datasets are FetaTab, PaperTab, SPIQA, SciGraphQA, and SlideVQA. Frozen slices live under `data/slices/`.

### 4.2 Processed documents

The systems consume the pinned Hugging Face processed representation, not independently reprocessed PDFs. Each document has a MinerU-style `_content_list.json` plus referenced images. This keeps the compared systems on the same parsing substrate.

### 4.3 Local models

Both executable paths use one OpenAI-compatible local endpoint:

| Role | Checkpoint |
|---|---|
| Vision-language generation | `/mnt/maxtox-nfs-student/zff/models/qwen2.5-vl-7b` |
| Embeddings | `/mnt/maxtox-nfs-student/zff/models/bge-m3` |

The validated V100 serving envelope is BF16 with SDPA, at most 20,000 input characters, at most 262,144 pixels per image, at most 1,024 generated tokens, expandable CUDA segments, and per-request CUDA cache cleanup. `environment/local_openai_server.py` exposes `/v1/chat/completions` and `/v1/embeddings`.

This is a controlled local backbone, not the paper-scale Qwen3-VL-32B model. Results test pipeline behavior under the available model; they do not reproduce the paper’s headline model scale.

## 5. Corrected released G²-Reader: offline Content Graph construction

The wrapper `baseline_original/scripts/run_corrected.py` resolves configuration, writes a run manifest, sets non-secret environment variables, and launches `scripts.test_rag` inside the patched worktree.

### Step 1: resolve the dataset row and documents

`scripts/test_rag.py` constructs `DAGPred`; `DAGPred.get_pred_dag()` eventually requests a memory system for the row. `prebuild/amem_new.py` loads the released dataset CSV and maps the question ID to processed directories.

Corrections made here include:

- normalize IDs such as `feta_tab_10447` before matching numeric source IDs;
- replace the hidden five-document slice with explicit `document_limit` configuration;
- include document limit and evolution rounds in the cache scope.

### Step 2: parse MinerU output

`utils/mineru_utils.py` contains two main extraction paths:

- `extract_chunk_from_mineru()` accumulates text into coarse chunks;
- `extract_image_from_mineru()` resolves tables/figures, captions, and nearby textual context.

Text and visual elements are processed separately and then inserted into one memory system.

### Step 3: analyze every evidence unit

`prebuild/amem_new.py::construct_memory()` launches analysis calls for text chunks and visual elements. The prompts ask the VLM for summary, keywords, and tags. Image requests include the encoded image plus neighboring context/caption.

The corrected path bounds concurrency. Failed text analysis receives explicit error/default metadata; failed visual analysis can be skipped. This explains why the corrected FetaTab graph retained 11 nodes while the minimal parser retained all 13 source elements.

### Step 4: embed summaries and keywords

The BGE endpoint embeds strings shaped like:

```text
<summary> keywords: <keyword 1>, <keyword 2>, ...
```

The original code referenced an embedding client that was never initialized. The corrected worktree configures a separate OpenAI-compatible embedding client.

### Step 5: create reading-order links

Each retained note links to nearby notes within the configured window. The released version only initialized this structure reliably for text; the correction includes visual nodes so a table or figure does not begin isolated merely because of modality.

Internally, released links are integer positions into `list(ms.memories.values())`, not stable source/target IDs. The corrected trace snapshot translates valid positions to explicit IDs for inspection.

### Step 6: evolve the graph

`AgenticMemorySystem.process_memory_single()` builds a candidate neighborhood from:

- semantic nearest neighbors;
- the node’s current links.

It sends the current node, neighbors, and any relevant images to the evolution prompt. The model may suggest connections and optionally revise the summary/keywords. Suggested links are capped, then the graph is re-embedded after every evolution round.

The released `_call_llm_evolve()` signature did not accept the caller’s `max_tokens` argument, causing evolution to fail and return unchanged nodes. The corrected signature accepts and forwards it. Evolution failures still return the original node, but now they are visible.

### Step 7: persist the graph

The released memory cache contains:

- `memories.pkl`;
- `retriever_embeddings.npy`.

The correction also writes a redacted `content_graph.json` containing stable node IDs, summaries, keywords, tags, modality, and explicit ID edges without copying raw image/base64 content into the audit artifact.

## 6. Corrected released G²-Reader: online question path

### Step 1: initial retrieval

`DAGPred.retriever()` and `retriever_split_sem_bm25()` query the cached memory system. The corrected baseline supports semantic retrieval and a real dependency-free BM25 implementation. Text and image budgets are configurable.

Although retrieval starts from a graph, the Worker does not receive a graph object. Selected notes are flattened into strings labeled `Related Memory`, with selected images attached separately. Explicit edges are kept in logs, not injected as extra facts.

### Step 2: Planning Graph generation

`DAGPred.dag_decomposer()` inserts the question and probing context into the released decomposition prompt. It tries up to three model responses, parses tagged/fenced/plain JSON, and validates:

- non-empty and unique node IDs;
- child references to existing nodes;
- maximum node count;
- absence of cycles;
- configured depth.

If all attempts fail, the correction produces a labeled single-node fallback rather than aborting invisibly.

One remaining nuance: the corrected `_compute_depth()` measures from a node named `root`; disconnected components or a graph without `root` are not handled as rigorously as the minimal validator. This should be treated as a remaining validation limitation.

### Step 3: execute dependencies first

`DAGPred._execute_dag()` builds an order and reverses it because parents consume children. For each non-root task, `_execute_dag_node()`:

1. retrieves local evidence using the task text;
2. obtains direct child answers already generated in the same round;
3. appends those child results to the flattened evidence context;
4. invokes the Worker/reasoner prompt;
5. stores the response under `(round, node_id)`;
6. records the response and retrieval log.

### Step 4: check evidence and refine

`_check_evidence_sufficiency()` sends the question, main context, and current round’s task/answer pairs to a VLM judge. This is a model judgment, not deterministic verification.

If insufficient, `dag_decomposer_after_check()` receives the prior DAG, evidence, and reported gaps. A new valid DAG is executed in full. Selective reuse is intentionally not implemented. The corrected path retains every round in `execution_trajectory`; upstream originally synthesized only from the final round.

### Step 5: final synthesis and evaluation

`reasoner_with_trajectory()` receives the original question, main retrieved context, attached images, and the accumulated task-answer trajectory. The response is extracted and evaluated. The compatibility evaluator accepts both `<output>` and `<answer>` tags because generation and evaluation disagreed in the release.

## 7. Minimal G²-Reader: design principles

The minimal implementation avoids the upstream mixture of global configuration, multiprocessing, cache state, retrieval, prompting, and logging. Its source modules each have one primary responsibility.

| Module | Responsibility |
|---|---|
| `config.py` | Load versioned model and graph parameters |
| `types.py` | Define every graph, evidence, answer, and trace boundary |
| `processed_chunks.py` | Convert processed documents into ordered coarse nodes |
| `graph_builder.py` | Orchestrate node analysis, initialization, evolution, and embedding |
| `resilient_graph.py` | Make graph-build failures explicit and deterministic |
| `content_graph.py` | Reading edges and graph serialization |
| `embeddings.py`, `remote_embeddings.py` | Mock/local embedding boundaries |
| `llm.py`, `structured.py` | Generation, timing, truncation, JSON parsing, bounded retries |
| `retrieval.py` | Deterministic semantic seed plus neighbor expansion |
| `planning_graph.py` | Planning schema, validation, and dependency order |
| `agents.py` | Planner, Worker, checker, refiner, final Reasoner prompts |
| `pipeline.py` | End-to-end online orchestration |
| `evaluation.py` | Answer extraction and deterministic metrics |
| `tracing.py` | Machine JSON and readable Markdown traces |
| `cli.py` | Build, show, and ask commands |

## 8. Minimal G²-Reader: typed state

`types.py` makes data movement explicit:

| Type | Meaning |
|---|---|
| `SourceLocation` | Document ID, element index, optional page |
| `ContentNode` | One text/visual evidence unit and retrieval metadata |
| `ContentEdge` | Directed source, target, and relation label |
| `ContentGraph` | Nodes plus edges |
| `PlanningNode` | One question-specific task |
| `PlanningEdge` | Parent-depends-on-child relationship |
| `PlanningGraph` | Tasks plus dependency edges |
| `RetrievedEvidence` | Selected node IDs, induced edges, scores, reasons |
| `IntermediateAnswer` | Worker result plus prerequisites and evidence IDs |
| `EvidenceCheck` | Model judgment, gaps, and rationale |
| `ExecutionTrace` | Complete per-question state trajectory |
| `FinalAnswer` | Extracted answer plus raw response |

These types make it possible to test dependency direction, retrieval budgets, round limits, and trace completeness without running the real VLM.

## 9. Minimal G²-Reader: offline Content Graph construction

### Step 1: ordered parsing and stable IDs

`processed_chunks.load_chunked_document()` scans `_content_list.json` in source order. Adjacent text is accumulated and split at the configured character limit. A non-text item flushes pending text and becomes one visual node.

Visual content uses table body, caption, or text metadata, and includes a data URL when the referenced image exists. `stable_node_id()` hashes document identity, source index, and modality so IDs remain stable across runs with identical input.

### Step 2: resilient node analysis

`resilient_graph.analyze_nodes_resilient()` asks for JSON keys `summary`, `keywords`, and `tags`. `structured.timed_generate_json()` allows three syntax-repair attempts and records timing/token/VRAM metadata for every attempt.

After three JSON failures, the node is not discarded. It receives:

- the first 500 characters as summary;
- deterministic regex keywords;
- tag `structured-output-fallback`.

### Step 3: embeddings and reading-order graph

`content_graph.initialize_graph()` embeds summary plus keywords and creates bidirectional reading-order edges within the configured window. With window two, each node links in both directions to up to two later neighbors.

### Step 4: graph evolution

For each round and node, `evolve_graph_resilient()` supplies the current summary/keywords plus current outgoing neighbors. The model may update summary/keywords and add bounded links to existing IDs. Invalid output leaves the node unchanged and records the failure. Every round ends with re-embedding all nodes.

Important current gap: `GraphConfig.semantic_candidates` exists, but the current minimal evolution function does not calculate semantic Top-K candidates. It only exposes nodes already connected by reading/evolved edges. The intended architecture calls for current neighbors plus semantic candidates; this is a known implementation gap to fix before calling the minimal graph builder fully architecture-faithful.

### Step 5: serialization and cache identity

The graph is plain JSON, including typed source locations, content metadata, embeddings, and edges. `scripts/run_experiment.py` hashes document list, chunk size, and node cap into the graph filename. It refuses to overwrite a non-empty run directory and writes resolved configuration/revisions to `run_manifest.json`.

## 10. Minimal G²-Reader: online question path

### Step 1: probing retrieval

`retrieval.retrieve()` embeds the question, cosine-ranks every Content Graph node, then processes ranked seeds deterministically:

1. take up to the configured `semantic_candidates` highest-ranked entry points;
2. interleave each semantic seed with one immediate graph neighbor so the first
   seed cannot consume the full budget;
3. prefer same-document neighbors in element-order proximity, then semantic
   score and stable ID;
4. expand remaining candidate neighbors round-robin and use semantic fill if
   space remains;
5. return selected IDs and the induced edges among them.

The trace records every score and whether a node was a `semantic_seed`,
`neighbor_of:<id>`, or `semantic_fill`.

### Step 2: initial planning

The Planner receives the question, raw content of probing nodes, and selected images. It must return `nodes` and `edges`, with `parent_id`/`child_id` edges.

`planning_graph.validate()` rejects:

- duplicate IDs;
- empty or excessive node sets;
- missing edge endpoints;
- cycles;
- excessive depth across the dependency order.

`execution_order()` directly computes child-first ordering.

Important current gap: `timed_generate_json()` retries syntactically invalid JSON, but it does not accept a schema validator callback. Planning schema validation happens later in `parse_planning_graph()`/`validate()`. Therefore syntactically valid but schema-invalid planner output can escape the three-attempt fallback boundary and abort a run. Node analysis can similarly expose missing-key errors not covered by its `ValueError` fallback. The retry boundary should eventually validate the operation-specific schema, not only JSON syntax.

### Step 3: Worker execution

For every Planning node in dependency order, the pipeline:

1. embeds the task;
2. retrieves a local Content subgraph;
3. gathers direct child/prerequisite answers;
4. serializes raw selected evidence and prerequisite answers;
5. calls `agents.work()`;
6. records an `IntermediateAnswer`.

Explicit Content Graph edges remain in the trace but are not added to the Worker prompt. This prevents the minimal system from receiving graph facts withheld from the corrected baseline.

### Step 4: checker and bounded refinement

`agents.check()` requests `sufficient`, `gaps`, and `rationale`. Scalar string gaps are normalized to a one-item list; this normalization was added after the first real FetaTab trace exposed character-by-character splitting.

If insufficient and below `refinement_limit`, `agents.refine()` receives the question, gaps, and old graph. The whole revised graph executes again. All answers across all rounds are retained. At the limit, the pipeline terminates even if the model still says evidence is insufficient.

### Step 5: final synthesis

`agents.synthesize()` receives every task/answer pair from every round and requests an `<output>` answer. `evaluation.extract_answer()` requires that configured tag. `evaluation.score()` supports scalar, dictionary, list, and stringified released answer formats and reports normalized exact match plus containment.

## 11. Side-by-side behavioral comparison

| Concern | Corrected released baseline | Minimal implementation |
|---|---|---|
| Primary node object | `MemoryNote` with global/runtime coupling | Typed `ContentNode` |
| Graph links | Integer memory positions internally | Stable string IDs |
| Parsing | Separate released text/image helpers | One ordered typed parser |
| Analysis concurrency | Async, bounded by runtime semaphore | Sequential current runner |
| Evolution candidates | Semantic candidates plus existing links | Existing reading/evolved neighbors only (gap) |
| Reading links | Corrected to cover all modalities | Bidirectional for all modalities |
| Retrieval | Semantic, BM25, or merged released path | Cosine seeds plus deterministic neighbor expansion |
| Worker graph input | Flattened evidence and images | Same raw evidence interface; edges trace-only |
| Planning representation | Nodes with `children` arrays | Separate node and edge arrays |
| Dependency execution | Reversed topological order after repair | Dependency-first order by construction |
| Structured fallback | Parser plus strict planner validation/retries | Syntax retries; downstream schema boundary still incomplete |
| Refinement | Full DAG rerun, all rounds retained after repair | Full DAG rerun, all rounds retained |
| Configuration | Patched globals populated from wrapper/env | Frozen dataclasses loaded from YAML |
| Persistence | Pickle, NumPy embeddings, redacted JSON snapshot | Portable typed JSON graph |
| Trace | Patched into released result/log structure | First-class `ExecutionTrace` JSON and Markdown |

## 12. What happened in the real FetaTab run

Question: “How many of the songs are from 1979?” Reference count: four.

### Corrected released baseline

- One document and one evolution round.
- Retained 11 graph nodes and 38 explicit snapshot edges.
- Planner produced a graph referencing a missing child on all three attempts.
- Strict validation rejected it and used the labeled single-node fallback.
- Final prediction: `1`.
- Exact match: `0.0`.
- Online time: 214.71 seconds using a cached Content Graph.

### Minimal implementation

- One document and one evolution round.
- Retained all 13 source nodes and produced 90 edges.
- Planner produced a valid nine-node Planning Graph.
- The same nine tasks executed for four rounds because the checker remained insufficient.
- Produced 36 Worker answers, 110 recorded model/embedding calls, and 179,735 recorded input tokens.
- Total build-plus-online time: 1,018.56 seconds.
- Peak allocated VRAM: 31,233,342,464 bytes.
- Final prediction: `1`; exact match `0.0`.

The trace shows a systematic evidence problem: many distinct tasks retrieved the same chart-ranking evidence and generated nearly identical answers. Refinement repeated the graph rather than finding the catalogue table needed to count four entries. This is why scaling the current behavior to thousands of calls would be wasteful before retrieval/refinement diagnosis.

The historical trace also contains character-split checker gaps. That parser bug was fixed afterward and covered by a regression test; the original run artifact was correctly left immutable.

## 13. What happened in the real PaperTab run

The one-document PaperTab minimal run completed without CUDA, HTTP, parser, or schema failure:

- 14 Content Graph nodes;
- 93 edges;
- four planning rounds with three tasks each;
- 12 Worker answers;
- 64 recorded calls;
- 74,646 input tokens and 7,014 output tokens;
- 382.21 seconds;
- 22,601,856,000 bytes peak VRAM.

It returned a broad description of multiple-embedding CNN behavior but omitted the required architecture names `standard CNN`, `C-CNN`, and `MVCNN`. Exact match and containment were both zero. This again points toward evidence selection and task effectiveness rather than an infrastructure failure.

## 14. Failure handling and observability

### Expected recoverable failures

- malformed JSON: bounded repair attempts;
- node analysis failure: deterministic summary/keyword fallback in the minimal path;
- graph evolution failure: retain unchanged node and record the event;
- upstream invalid Planning Graph: strict retries, then labeled single-node fallback;
- insufficient evidence: bounded full-graph refinement;
- context overflow risk: explicit head-tail truncation plus service envelope;
- CUDA fragmentation risk: expandable segments and per-request cache cleanup.

### Failures that should stop a run

- missing processed documents;
- missing API-key environment variable;
- invalid or cyclic minimal Planning Graph after the current downstream validation boundary;
- attempt to overwrite a non-empty result directory;
- model server or embedding endpoint failure after client error propagation;
- invalid final answer tag in the minimal evaluator.

Every expensive run should have a unique directory containing `run_manifest.json`, predictions, graphs or graph references, machine traces, and human traces.

## 15. How to read a trace

Start with the Markdown trace for a quick explanation, then open the JSON for exact fields.

Read in this order:

1. **Probing retrieval:** Were the right table/figure/text nodes selected?
2. **Planning graph:** Did tasks correspond to the operations actually needed?
3. **Execution order:** Did children appear before parents?
4. **Worker evidence IDs:** Did different tasks retrieve meaningfully different evidence?
5. **Worker answers:** Are answers grounded in the supplied evidence?
6. **Evidence check:** Did the judge identify the real missing information?
7. **Refinement:** Did the graph or retrieval behavior actually change?
8. **Final answer:** Did synthesis use the strongest evidence or repeat an early mistake?
9. **Runtime section:** Were retries, truncations, token use, wall time, or VRAM abnormal?

For FetaTab, use:

- `results/smoke/runs/minimal_matched_plumbing_20260818T0108/traces/feta_tab_10447.md`
- `results/smoke/runs/minimal_matched_plumbing_20260818T0108/traces/feta_tab_10447.json`

For corrected upstream, use:

- `results/smoke/runs/corrected_real_plumbing_v9/traces/feta_tab_10447.md`
- `results/smoke/runs/corrected_real_plumbing_v9/traces/feta_tab_10447.json`

## 16. Why the full smoke run is not running now

The 15-question smoke slice contains 5,804 estimated Content Graph nodes. With initial analysis plus three intended evolution rounds, graph construction alone requires at least 23,216 VLM calls and as many as 69,648 structured attempts before online planning/Workers/checking.

The cost comes from per-node VLM work:

```text
minimum graph calls = nodes × (1 analysis + evolution rounds)
```

At the current single-V100 latency, this is not a one-night experiment. It would also scale behavior that has already failed on two inspected answers. The sensible next step is to repair systematic retrieval/refinement weaknesses and close the known minimal implementation gaps, then rerun the small examples before committing benchmark-scale compute.

## 17. Practical commands

Run all normal tests:

```bash
cd /mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab
source .venv/bin/activate
python -m pytest baseline_original/tests minimal_g2_reader/tests -q
```

Start the shared endpoint:

```bash
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python environment/local_openai_server.py \
  --vlm /mnt/maxtox-nfs-student/zff/models/qwen2.5-vl-7b \
  --embedding /mnt/maxtox-nfs-student/zff/models/bge-m3 \
  --host 127.0.0.1 --port 18000 \
  --max-visual-pixels 262144 \
  --max-output-tokens 1024 \
  --max-input-characters 20000
```

Build and inspect one minimal graph:

```bash
minig2 build --config minimal_g2_reader/configs/dev.yaml \
  --processed-root data/processed_hf \
  --dataset feta_tab \
  --document 'London Calling (song).pdf' \
  --output results/smoke/manual/london.content_graph.json

minig2 show --graph results/smoke/manual/london.content_graph.json
```

Execute one question against that graph:

```bash
export MINIG2_API_KEY=local
minig2 ask --config minimal_g2_reader/configs/dev.yaml \
  --graph results/smoke/manual/london.content_graph.json \
  --question-id feta_tab_10447 \
  --question 'How many of the songs are from 1979?' \
  --trace-dir results/smoke/manual/traces
```

## 18. Recommended next engineering work

The order matters:

1. Add semantic Top-K candidate construction to minimal graph **evolution** and
   test that it changes the candidate set deterministically. This remains
   separate from the now-operational multi-candidate online retrieval.
2. Evaluate Planner dependency semantics and checker false-positive rates over
   a larger frozen slice; both available examples produced backward useful
   information flow.
3. Add retrieval recall and evidence-entailment measurements so answer-bearing
   evidence can be distinguished from VLM reasoning errors.
4. Make refinement measurably react to gaps—through changed tasks or retrieval
   queries—without dataset-specific prompt tuning.
5. Ingest the remaining SlideVQA, SPIQA, and SciGraphQA representatives before
   further prompt changes, then evaluate them in increasing estimated cost
   order.
6. Choose either additional compute for the paper-intended smoke configuration
   or a clearly versioned reduced-budget profile applied identically to both
   implementations.

## 19. Related documentation

- `docs/upstream_code_walkthrough.md` — compact released runtime path
- `docs/upstream_audit.md` — eleven requested audit findings
- `docs/additional_runtime_findings.md` — six execution-discovered findings
- `docs/paper_vs_code.md` — paper/release discrepancies
- `docs/baseline_repairs.md` — every corrected baseline repair
- `docs/minimal_architecture.md` — minimal architecture summary and extension boundary
- `docs/experiment_protocol.md` — comparison rules
- `docs/comparison_report.md` — real execution outcome
- `docs/completion_audit.md` — definition-of-done status
- `results/comparisons/smoke_comparison.md` — one-question comparison and resource gate

## 20. Short glossary

- **MinerU:** preprocessing format that provides ordered text and visual elements.
- **Content Graph:** persistent graph of document evidence units.
- **Planning Graph / DAG:** per-question dependency graph of reasoning tasks.
- **Reading-order edge:** link between nearby source elements.
- **Evolution edge:** model-suggested relationship between candidate evidence nodes.
- **Semantic seed:** node selected by embedding similarity.
- **Neighbor expansion:** adding linked nodes around a semantic seed.
- **Worker:** model call that answers one Planning node from local evidence and prerequisite answers.
- **Checker:** model judgment of whether current intermediate answers are sufficient.
- **Refiner:** model call that revises the Planning Graph from identified gaps.
- **Reasoner:** final synthesis call over the accumulated trajectory.
- **Trace:** immutable record of retrieval, graphs, execution order, answers, checks, calls, and resource use.

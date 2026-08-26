I want to identify a concrete way to improve G²-Reader’s multimodal QA accuracy and runtime. Before implementing anything, read:

- Minimal implementation: https://github.com/ffaisal93/minimal_g2_reader
- Official G²-Reader: https://github.com/DorothyDUUU/G2_Reader
- Paper and OpenReview discussion: https://openreview.net/forum?id=1NACQKPp1n

Pay particular attention to retrieval, Planning Graph execution, Worker reasoning, evidence checking, replanning, tracing and final synthesis.

The OpenReview rebuttal reports the following proportions among G²-Reader failures:

- retrieval failure: 42.9%;
- final reasoning failure: 34.7%;
- decomposition failure: 18.4%;
- replanning/sufficiency failure: 4.1%.

The authors have also tested retrieval corruption by replacing top-ranked evidence with distractors. Therefore, do not position our work as the first study of error propagation or retrieval corruption.

Our unanswered question is narrower:

> When G²-Reader retrieves the correct multimodal evidence, how often does a Worker misinterpret the table, figure, text, value, unit or relationship, and how often does that unsupported intermediate answer propagate through the Planning Graph?

The proposed direction is a modality-aware node diagnosis and local-repair layer:

```text
Planning node
    → local Content Graph retrieval
    → Worker answer
    → diagnose the result
        → evidence missing: expand local retrieval
        → table misread: extract the relevant cells
        → figure misread: crop/zoom and reinterpret the figure
        → calculation error: use deterministic calculation
        → composition error: rerun only the affected parent
    → pass the corrected result upward
```

The verifier must not add a large-model call to every node. G²-Reader already has substantial online latency. Use cheap deterministic checks first, and invoke multimodal semantic verification only for risky or ambiguous nodes.

## First experiment

Use approximately 100 SPIQA questions. Keep the model, Content Graph configuration, retrieval budget, Planning Graph limits and random seed fixed.

Run the unmodified Minimal G²-Reader and save complete traces. For each incorrect final answer, classify the primary failure as:

1. `retrieval_failure`: the necessary evidence was not retrieved;
2. `worker_support_failure`: the evidence was retrieved, but the Worker’s answer was not supported by it;
3. `decomposition_failure`: the Planning Graph omitted or misstated a required subproblem;
4. `composition_failure`: intermediate answers were supported, but a parent or final answer combined them incorrectly;
5. `sufficiency_failure`: the checker terminated despite an identifiable unresolved gap;
6. `unverifiable`: the retrieved visual node was too coarse or unreadable to judge.

For every Worker-support failure, also record:

- modality: text, table, figure, text+table or text+figure;
- whether the answer was numerical or comparative;
- retrieved evidence-node IDs;
- whether the error propagated to ancestors;
- whether the global sufficiency checker returned `true`.

This first stage is post-hoc diagnosis only. It must not change retrieval, generation or the final answer.

Report:

- accuracy on the selected slice;
- frequency of each failure type;
- percentage of cases where correct evidence was present but misinterpreted;
- unsupported intermediate-answer rate;
- false-sufficient rate;
- propagation depth or number of affected ancestors;
- latency, token use and model-call count.

## First repair experiment

Only after the failure audit, choose the most common repairable Worker-support failure. If table-based numerical or comparative errors are sufficiently common, implement this first:

1. Require the Worker to return an answer, cited evidence-node IDs, extracted values, units and operation.
2. Check that the cited nodes were actually retrieved.
3. Verify table values, labels and units against the cited evidence.
4. Execute numerical calculations deterministically.
5. If verification fails, extract the relevant table rows/columns and rerun that Worker once.
6. Recompute only Planning Graph ancestors that depend on the corrected node.
7. Fall back to existing global replanning only if local repair fails.

Compare:

- A: original Minimal G²-Reader;
- B: original system plus post-hoc diagnosis, with no behavioral change;
- C: selective verification plus one local repair.

Measure:

- final-answer accuracy;
- intermediate-answer support rate;
- repair success rate;
- global replanning frequency;
- model calls;
- tokens;
- latency.

Before changing code, provide:

1. An assessment of whether the repository traces contain all required evidence.
2. Exact modules and data structures requiring modification.
3. A procedure for distinguishing retrieval, Worker, decomposition, composition and sufficiency failures.
4. A plan for selecting the 100 SPIQA questions.
5. A minimal annotation format.
6. A minimal implementation sequence.
7. Expected experimental confounds.
8. How the local repair can save enough global replanning cost to offset verification overhead.

Do not initially implement counterfactual documents, provenance-constrained graph evolution, scientific ontologies, conflict datasets or verification for every modality. First determine the dominant failure mechanism and implement one targeted repair.
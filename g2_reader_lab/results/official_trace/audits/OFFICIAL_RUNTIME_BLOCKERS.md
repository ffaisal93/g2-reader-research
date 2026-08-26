# Official G²-Reader runtime blockers observed before the SPIQA audit

These failures were observed while executing the official source plus passive tracing. They are infrastructure/runtime blockers, not question-answering errors, so their runs are excluded from the accuracy failure taxonomy.

## Gate v1: undefined embedding client

- Run: `qwen3_official_fidelity_gate_v1`
- Outcome: invalid and interrupted after approximately 28.8 minutes.
- Evidence: all 149 text analyses completed, then every text-embedding request failed with `name 'embed_aclient' is not defined`.
- Consequence: both official retrievers caught the construction exception, returned empty text and images, and allowed Planning Graph execution to continue without evidence.
- Repair: bind `embed_aclient` to the configured embedding endpoint and make retrieval construction exceptions fail the question instead of becoming an empty evidence set.

## Gate v2: graph evolution invocation mismatch

- Run: `qwen3_official_fidelity_gate_v2`
- Outcome: invalid and interrupted during the evolution stage.
- Evidence: 107/107 text analyses and embeddings and 72/72 image analyses and embeddings succeeded. All evolution tasks then reported `AgenticMemorySystem._call_llm_evolve() got an unexpected keyword argument 'max_tokens'`.
- Cause: released source calls `_call_llm_evolve(..., max_tokens=2048)`, while its function signature does not accept `max_tokens`.
- Consequence: the per-note exception handler silently retained every original note, so the run would have claimed one evolution round without performing LLM evolution.
- Repair: accept the already-supplied `max_tokens` argument and pass it unchanged to the OpenAI-compatible request.

## Released cache-path mismatch

- Saved graph directories are named `<question_id>_iter_<round>`.
- The released existence check tests only `<question_id>`, so saved evolved graphs are never loaded on a later process.
- Repair: test and load the exact final-round directory. This changes persistence/resumption only; graph prompts and algorithms are unchanged.

## Gate v3: optional judge field crashes final logging

- Run: `qwen3_official_fidelity_gate_v3`
- Outcome: invalid as a completed prediction artifact, although its reasoning trace is complete.
- Evidence: the Content Graph evolved successfully, retrieval returned evidence, refinement reached `sufficient=True`, and final synthesis completed. The process then raised `KeyError: 'judge'` while formatting a log line.
- Cause: the released logger reads `item['judge']` unconditionally even when evaluation judging is disabled and the input row has no `judge` field.
- Repair: use `item.get('judge')` in that log statement. This does not alter the prediction or any model input.

## Gate v4: successful plumbing gate, excluded from fixed-seed measurements

- Run: `qwen3_official_fidelity_gate_v4`
- Outcome: completed successfully in approximately 95 seconds by loading the validated evolved graph. It produced prediction, retrieval and passive trace artifacts.
- Protocol finding: the released chat calls do not send a sampling seed even though Planning Graph generation uses temperature 0.5 and graph evolution uses temperature 0.7.
- Decision: retain v4 as a runtime/plumbing validation, but exclude it and its interrupted pilot from measured results. The measured v5 sequence sends seed 42 to every preprocessing, evolution, planning, Worker, checker and synthesis chat call and sets `PYTHONHASHSEED=42`.

## Pilot v5: truncated structured image analysis was silently accepted

- Run: `qwen3_official_fixedseed_pilot5_v5`, question `spiqa_58`.
- Outcome: invalid and interrupted before the evolved graph was saved.
- Evidence: one image-analysis response reached the 8,192-token generation limit while repeating OCR axis values. JSON parsing failed, after which released preprocessing substituted `image analysis failed` and continued with `51/52` successful image analyses.
- Consequence: the pipeline would have embedded all 52 image slots and built a Content Graph containing one default/failure note. That makes downstream retrieval and accuracy diagnosis uninterpretable.
- Repair: retry an invalid or length-truncated structured-analysis call once with the same model and fixed retry seed (`43`), a 4,096-token cap, and compact-output constraints. The retry changes only error recovery; the original prompt, graph algorithm and successful-call behavior remain unchanged. Any question still reporting a nonzero text/image analysis or note-add failure is rejected by the sequence validator.
- Artifact policy: retain the failed response and question logs. Quarantine the partial `spiqa_58_iter_0` graph so it cannot be loaded by the replacement pilot.

## Pilot v6: compact prompting alone did not stop repeated OCR

- Run: `qwen3_official_fixedseed_pilot5_v6`, question `spiqa_58`.
- Outcome: invalid and interrupted at the start of graph evolution.
- Evidence: the same distractor image (Figure 1 from `1805.07567v2`) added an unrequested `text_content` field and repeated axis ticks. Attempt 1 reached 8,192 tokens; the seed-43 compact retry repeated the same field and reached its 4,096-token cap. Released preprocessing again reported `51/52` successful image analyses and one failed visual note.
- Decision: compact natural-language instructions are insufficient for this model/image pair. The v6 partial graph and both raw responses are retained but excluded.
- Repair: keep successful first attempts unchanged. On an invalid/truncated response only, request the official three-field contract (`keywords`, `summary`, `tags`) with vLLM JSON-schema enforcement, forbid additional properties, and bound summary length. A direct replay of the exact failing image stopped normally in 17.477 seconds, returned all three required fields, no extra field, and valid JSON (939 characters).

## Pilot v7: released prompt/schema disagrees with released image-note consumer

- Run: `qwen3_official_fixedseed_pilot5_v7`, question `spiqa_58`.
- Outcome: invalid and interrupted at the start of graph evolution.
- Evidence: strict retry enforcement recovered the pathological image and preprocessing reported `52/52` valid analyses. Image-note insertion nevertheless reported `51 successful, 1 failed`.
- Cause: the released image-analysis prompt requests only `keywords`, `summary`, and `tags`, but released note insertion unconditionally reads a fourth field, `text_content`. Normal unconstrained model replies happened to add that unrequested field; the first strict schema correctly excluded it and thereby exposed the latent contract mismatch.
- Repair: the error-only retry schema now includes the field the released consumer actually requires. `text_content` is capped at 2,400 characters to prevent repeated OCR. An exact-image replay stopped normally in 25.378 seconds, returned all four required fields, produced 476 characters of nonrepeated `text_content`, and parsed successfully.

## Audit policy

The failed gates and their logs are retained. A run enters the five-question pilot only after one question produces a non-empty prediction, retrieval artifact, and passive execution trace using a successfully constructed and evolved Content Graph. The 100-question audit starts only after the five-question pilot passes the same artifact checks.

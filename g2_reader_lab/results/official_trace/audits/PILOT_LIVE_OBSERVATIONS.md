# Official G² SPIQA Pilot: Live Observations

This notebook records observations made while supervising the fixed-seed five-question fidelity pilot. It is not an experiment input and does not alter the official G² runtime.

## `spiqa_542`

- Completed successfully on attempt 1.
- Prediction: `RCE`; reference: `RCE`.
- Existing validated 179-node evolved graph was reused.
- Full retrieval, planning, worker, checker, final, usage, and passive-trace artifacts are present.

## `spiqa_58`

- Completed successfully on attempt 1 in 3,360.84 seconds.
- Prediction explains the filter-generation and adaptive-convolution modules; it is semantically consistent with the reference.
- Cold graph: 130/130 text analyses, 52/52 visual analyses, 182/182 evolution calls.
- One unconstrained visual-analysis response ended at the token limit. The raw response was preserved as `failed_response_20260820_204206_642173.txt`; the error-only strict four-field schema retry succeeded.
- The checker declared `sufficient=True` in round 0.

## `spiqa_540`

- Completed successfully on attempt 1 in 4,321.79 seconds.
- Prediction: `DMRNet`; reference: `DMRNet` (exact match).
- Cold graph: 162/162 text analyses, 41/41 visual analyses, four official `No meaningful information` text-node filters, 199/199 evolution calls.
- One unconstrained visual-analysis response ended at the token limit. The raw response was preserved as `failed_response_20260820_214019_703807.txt`; the error-only strict four-field schema retry succeeded.
- The Planner created sibling tasks `n1` (extract average path lengths) and `n2` (compare the identified average path lengths). `n2` did not depend on `n1`; it performed its own retrieval and still produced the correct result. This is a planning-graph structural observation, not an answer failure.
- The checker declared `sufficient=True` in round 0.

## `spiqa_108`

- Completed successfully on attempt 1 in 2,585.40 seconds.
- The prediction is semantically consistent with the reference: ESMM-NS and ESMM outperform the other models across training-set sizes for both CVR and CTCVR.
- Cold graph: 106/106 text analyses, 63/63 visual analyses, 169/169 evolution calls; no structured-output retry was needed.
- The two sibling Workers separately handled the CVR and CTCVR charts. The checker declared `sufficient=True` in round 0.
- The final response goes beyond the qualitative reference by supplying visually estimated AUC values at every sampling rate. These extra values require source-level support inspection during the faithfulness audit even though the requested qualitative conclusion is correct.

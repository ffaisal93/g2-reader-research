# Resumable SPIQA-100 Failure Audit

Run the complete audit in a detached session:

```bash
cd /mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab
tmux new-session -d -s g2_audit100_runner \
  'bash experiments/failure_audit_100/supervise_audit.sh >> experiments/failure_audit_100/runner.log 2>&1'
```

The same command can be run again after interruption. Validated graphs and
queries are skipped. Partial failures are archived before retry.
The supervisor restarts the runner after an unexpected nonzero exit; a normal
completed pass stops cleanly for post-hoc review.

Monitor without modifying the run:

```bash
jq '{build_complete,query_complete,query_failed,parsed_prediction_missing}' \
  experiments/failure_audit_100/PROGRESS.json
tail -f experiments/failure_audit_100/runner.log
```

Refresh the behavior-neutral trace review queue at any checkpoint:

```bash
.venv/bin/python experiments/failure_audit_100/summarize_traces.py
.venv/bin/python experiments/failure_audit_100/prepare_review_packets.py
```

`review_packets/` then contains compact Planning Graph, retrieval, Worker,
sufficiency, and synthesis evidence for causal failure attribution. The script
does not guess the causal label automatically.

The official traced source is not edited. This run is explicitly labeled as
the optimized-8B low-resource baseline; failure attribution against original
32B G2 is a separate validation step.

`REPORT.md` contains regenerated live status plus the persistent observations
from `FINDINGS.md`. Add durable human-reviewed findings to `FINDINGS.md`; the
runner will preserve them whenever it refreshes the report.

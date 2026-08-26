#!/usr/bin/env bash
set -u

LAB=/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab
ROOT="$LAB/experiments/failure_audit_100/posthoc_adjudication"
LOG="$ROOT/finalizer.log"

cd "$LAB" || exit 1
printf '%s waiting for targeted replay session\n' "$(date --iso-8601=seconds)" >> "$LOG"
while tmux has-session -t g2_audit100_replays 2>/dev/null; do
    sleep 30
done

if ! .venv/bin/python - <<'PY'
import json
from pathlib import Path
p = Path("experiments/failure_audit_100/posthoc_adjudication/REPLAY_PROGRESS.json")
x = json.loads(p.read_text())
raise SystemExit(0 if x.get("finished_at") else 1)
PY
then
    printf '%s replay session ended early; resuming from checkpoints\n' "$(date --iso-8601=seconds)" >> "$LOG"
    .venv/bin/python -u "$ROOT/run_targeted_replays.py" >> "$LOG" 2>&1
fi

printf '%s starting replay adjudication\n' "$(date --iso-8601=seconds)" >> "$LOG"
.venv/bin/python "$ROOT/adjudicate_replays.py" >> "$LOG" 2>&1
.venv/bin/python "$ROOT/build_posthoc_report.py" >> "$LOG" 2>&1
printf '%s finalization complete\n' "$(date --iso-8601=seconds)" >> "$LOG"

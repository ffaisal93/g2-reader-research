#!/usr/bin/env bash
set -uo pipefail

lab_root=/mnt/maxtox-nfs-student/zff/g2-reader/g2_reader_lab
runner=$lab_root/experiments/failure_audit_100/run_resumable_audit.py

cd "$lab_root"
while true; do
  printf '[AUDIT SUPERVISOR] starting/resuming at %s\n' "$(date --iso-8601=seconds)"
  "$lab_root/.venv/bin/python" -u "$runner"
  return_code=$?
  printf '[AUDIT SUPERVISOR] runner exited rc=%s at %s\n' "$return_code" "$(date --iso-8601=seconds)"
  if [[ $return_code -eq 0 ]]; then
    break
  fi
  printf '[AUDIT SUPERVISOR] unexpected exit; restarting from checkpoints in 10 seconds\n'
  sleep 10
done

"$lab_root/.venv/bin/python" "$lab_root/experiments/failure_audit_100/summarize_traces.py" || true
"$lab_root/.venv/bin/python" "$lab_root/experiments/failure_audit_100/prepare_review_packets.py" || true

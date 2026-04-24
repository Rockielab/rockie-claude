#!/usr/bin/env bash
# launch_experiment.example.sh — a TEMPLATE launcher for the autopilot loop.
#
# Copy this into your project's scripts/ (or wherever LAUNCHER_CMD in your
# .claude/autopilot.conf points) and edit for your training code.
#
# Contract:
#   1. Reads one queue-item JSON on stdin. Example shape:
#        {"id": 42, "priority": 2, "hypothesis": "…",
#         "metric_name": "val_loss", "predicted_delta": -0.05,
#         "lower_is_better": 1, "estimated_minutes": 45,
#         "suggested_stage": "creative", "parent_experiment_id": null}
#
#   2. Starts the actual training process in the BACKGROUND (nohup + &).
#      The autopilot loop waits on the PID you record, not on this script.
#      This script itself must return quickly (within seconds) so the
#      autopilot can hand over to ZCM polling.
#
#   3. Writes the PID of the detached training process to $PID_FILE.
#
#   4. Tees the training stdout+stderr to $LOG_FILE. ZCM watches this file
#      for anomaly patterns (NaN, OOM, shape errors, plateau, …).
#
# The example below launches a toy torch script. Replace with your own.

set -euo pipefail

PID_FILE="${PID_FILE:-.claude/.state/training_pid}"
LOG_FILE="${LOG_FILE:-.claude/.state/training_log}"
mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

# Parse queue item JSON from stdin.
ITEM_JSON=$(cat)
QUEUE_ID=$(printf '%s' "$ITEM_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
HYPOTHESIS=$(printf '%s' "$ITEM_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("hypothesis",""))')
STAGE=$(printf '%s' "$ITEM_JSON"      | python3 -c 'import sys,json;print(json.load(sys.stdin).get("suggested_stage",""))')

echo "[launcher] queue_id=$QUEUE_ID stage=$STAGE"
echo "[launcher] hypothesis: $HYPOTHESIS"

# Pre-flight: register a dry-run sentinel for the training script.
# (In real use, do a genuine forward+backward smoke test BEFORE this step
# and only register the sentinel if that smoke test passes.)
TRAIN_SCRIPT="src/train.py"
if [ ! -f "$TRAIN_SCRIPT" ]; then
  echo "[launcher] error: $TRAIN_SCRIPT not found — edit this template for your code" >&2
  exit 2
fi

# Register the sentinel (stub — your real launcher should do a 2-step
# dry-run and only register on success).
bash .claude/scripts/dry_run_gate.sh register "$TRAIN_SCRIPT" >/dev/null

# Detach the real training process. `nohup … &` puts it in the background;
# disown removes it from our job table so our exit doesn't signal it.
: > "$LOG_FILE"
nohup python3 "$TRAIN_SCRIPT" --queue-id "$QUEUE_ID" >> "$LOG_FILE" 2>&1 &
TRAIN_PID=$!
disown $TRAIN_PID 2>/dev/null || true

echo "$TRAIN_PID" > "$PID_FILE"
echo "[launcher] detached pid=$TRAIN_PID log=$LOG_FILE"

# Return fast. ZCM takes over.
exit 0

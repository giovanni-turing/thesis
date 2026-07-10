#!/bin/bash
# Redesigned closed-loop predictor benchmark — run ONE (predictor, window) cell.
#
# Isolates the load-predictor's effect on the SLA planner's closed-loop schedule.
# Prior version (burst3) was discarded: p99 TTFT saturated on the worst long-prefill
# and predictors had too little history. This redesign uses a decode-bound window
# (steady24h, ITL-binding, 24h history) or a slow-onset burst (burst4).
#
# Usage: run_one.sh <predictor: arima|kalman|prophet> <window: steady24h|burst4>
set -euo pipefail
PRED=${1:?predictor arima|kalman|prophet}
WIN=${2:?window steady24h|burst4}

BASE=/home/gio/tese/.claude/worktrees/agent-a8d707cf6d783f2b7/simulation
OUT=$BASE/results/predictor_closedloop_v2
CFG=$OUT/configs/planner_${PRED}.json

case "$WIN" in
  steady24h)
    TRACE=$BASE/results/grid/traces/grid_steady24h_C2.jsonl
    export AIC_TP=1 ; N=2 ;;              # steady24h: tp_star=1, n_star=2
  burst4)
    TRACE=$BASE/results/grid/traces/grid_burst4_C7.jsonl
    export AIC_TP=2 ; N=2 ;;              # burst4: tp_star=2, n_star=2
  *) echo "window must be steady24h|burst4" >&2; exit 2 ;;
esac

REPORT=$OUT/$WIN/${PRED}.report.json
LOG=$OUT/$WIN/${PRED}.log

export REPLAY_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
export AIC_VER=0.19.0
export STARTUP_TIME=60

echo "[run_one] pred=$PRED win=$WIN AIC_TP=$AIC_TP N=$N"
echo "[run_one] trace=$TRACE"
echo "[run_one] cfg=$CFG report=$REPORT"

# run_replay.sh cd's to $AIC; pass ABSOLUTE paths. Use the SHARED runner (identical
# to the worktree copy) so the harness matches the prior sound runs exactly.
# NOTE: run_replay.sh `exec`s the python process; piping its stdout through `tee`
# across that exec under `pipefail` dropped the log file, so we redirect the whole
# invocation to $LOG with a subshell instead (reliable, and strips no output).
# The replay process exits non-zero during interpreter teardown AFTER writing the
# full report.json + metrics table (benign atexit/loop-close artifact), so we do
# not let that mask a real failure: we check the report exists and is valid JSON.
set +e
( /home/gio/tese/simulation/run_replay.sh "$TRACE" aic "$REPORT" "$N" \
    --planner-config "$CFG" ) > "$LOG" 2>&1
rc=$?
set -e
if [ -f "$REPORT" ] && "$REPLAY_PY" -c "import json,sys; json.load(open('$REPORT'))" 2>/dev/null; then
  echo "[run_one] DONE pred=$PRED win=$WIN -> $REPORT (replay rc=$rc; report valid)"
  exit 0
else
  echo "[run_one] FAIL pred=$PRED win=$WIN: no valid report (replay rc=$rc)" >&2
  exit 1
fi

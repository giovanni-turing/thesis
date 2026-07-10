#!/bin/bash
# Extend the reactive-ENCODER baseline to burst2 and burst6 (the two burst
# episodes in the trace's first 1.4 days, previously graded only by static grid
# + LLM reactive). The reactive encoder policy needs no forecast — it reads the
# OBSERVED image rate from the trace — so it CAN run on these two windows.
#
# Mirrors simulation/run_44_aggregate.sh run_policy(... reactive ...):
#   rho=15, hysteresis 3min, resolution 15s, encoder-workers 2.
# Grid: {burst2, burst6} x cold-start lead L in {15, 30, 45, 300} s.
set -u
ROOT=/home/gio/tese/.claude/worktrees/agent-a74616313adef0c5e
OUT=$ROOT/simulation/results/burst26_reactive
mkdir -p "$OUT"
EDA_PY=/home/gio/tese/eda/.venv/bin/python
AIC_PY=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
CONV=$ROOT/workload/trace_to_two_pool.py
SCHED=$ROOT/simulation/forecast_schedule.py
export TESE_WINDOWS=$ROOT/simulation/windows.json

# window offset/max_requests from windows.json
declare -A OFFSET=( [burst2]=78376 [burst6]=93867 )
declare -A NREQ=(   [burst2]=13870 [burst6]=9821 )

run_cell() {  # $1 window  $2 lead_s
  local WIN=$1 L=$2
  local TAG=${WIN}_react_L${L}
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $EDA_PY $SCHED --window "$WIN" --policy reactive --resolution 15s \
      --quantile p90 --rho 15 --cold-start-s "$L" --hysteresis-min 3 \
      --parquet /home/gio/tese/predictors/results/chronos_images.parquet \
      --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 \
      || { echo "SCHED FAIL $TAG"; return; }
  $AIC_PY $CONV --out "$OUT/$TAG.jsonl" --offset "${OFFSET[$WIN]}" \
      --max-requests "${NREQ[$WIN]}" --encoder-workers 2 \
      --worker-schedule "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

run_cell "$@"

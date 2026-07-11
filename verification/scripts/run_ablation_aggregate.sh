#!/bin/bash
# Aggregate-only re-run (clean sequential gen; converters 3-way parallel).
set -u
EDA=/home/gio/tese/eda/.venv/bin/python
AIC=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
RQ=/home/gio/tese/verification/scripts/reactive_quantile_schedule.py
CONV=/home/gio/tese/workload/trace_to_two_pool.py
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json
O=/home/gio/tese/simulation/results/rerun_verify
OFF=250399; NRQ=749601

# 1) generate all six schedules sequentially, verifying each file
for L in 30 300; do
  for RW in 120 240 480; do
    TAG="react_p90_W${RW}_aggregate_L${L}"
    $EDA $RQ --window aggregate --mode react_quantile --quantile p90 --react-window-s "$RW" \
      --resolution 15s --rho 15 --cold-start-s "$L" --hysteresis-min 3 \
      --out "$O/$TAG.sched.json" > "$O/$TAG.sched.log" 2>&1
    if [ -s "$O/$TAG.sched.json" ]; then echo "sched OK $TAG ($(wc -c < "$O/$TAG.sched.json") B)";
    else echo "SCHED FAIL $TAG"; cat "$O/$TAG.sched.log"; fi
  done
done

# 2) run converters, 3-way parallel
run() {
  local TAG=$1
  [ -f "$O/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $AIC $CONV --out "$O/$TAG.jsonl" --offset "$OFF" --max-requests "$NRQ" \
    --encoder-workers 2 --worker-schedule "$O/$TAG.sched.json" \
    > "$O/$TAG.sim.log" 2>&1 && { rm -f "$O/$TAG.jsonl"; echo "done $TAG"; } \
    || { echo "FAIL $TAG"; tail -3 "$O/$TAG.sim.log"; }
}
for L in 30 300; do
  for RW in 120 240 480; do
    run "react_p90_W${RW}_aggregate_L${L}" &
    while [ "$(jobs -r | wc -l)" -ge 3 ]; do wait -n; done
  done
done
wait
echo "AGG ABLATION DONE $(date -u +%H:%M:%S)"

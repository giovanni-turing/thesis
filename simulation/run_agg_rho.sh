#!/bin/bash
set -u
AIC_PY=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
EDA_PY=/home/gio/tese/eda/.venv/bin/python
CONV=/home/gio/tese/workload/trace_to_two_pool.py
SCHED=/home/gio/tese/simulation/forecast_schedule.py
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json
OUT=/home/gio/tese/simulation/results/aggregate44_rho
run() { # rho lead
  local R=$1 L=$2 TAG="fc_p90_rho${R}_L${L}"
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $EDA_PY $SCHED --window aggregate --policy forecast --resolution 15s \
    --quantile p90 --rho $R --cold-start-s $L --hysteresis-min 3 \
    --parquet /home/gio/tese/predictors/results/chronos_images.parquet \
    --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return; }
  $AIC_PY $CONV --out "$OUT/$TAG.jsonl" --offset 250399 --max-requests 749601 \
    --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
    > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}
for R in 10 20 25; do for L in 30 300; do run $R $L & done; done
wait
echo "agg-rho done $(date -u +%H:%M:%S)" >> "$OUT/status.txt"

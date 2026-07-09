#!/bin/bash
# Model-sensitivity rider for table 8.2: the p90 aggregate schedules
# regenerated from the toto and timesfm archives (chronos = the table's
# rows). Same span, rho15, 15s, hyst 3min, leads {30,300}.
set -u
OUT=/home/gio/tese/simulation/results/aggregate44
EDA_PY=/home/gio/tese/eda/.venv/bin/python
AIC_PY=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
CONV=/home/gio/tese/workload/trace_to_two_pool.py
SCHED=/home/gio/tese/simulation/forecast_schedule.py
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json

run_policy() {  # $1 tag  $2 model  $3 lead_s
  local TAG=$1 M=$2 L=$3
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $EDA_PY $SCHED --window aggregate --policy forecast --resolution 15s \
      --quantile p90 --rho 15 --cold-start-s "$L" --hysteresis-min 3 \
      --parquet /home/gio/tese/predictors/results/${M}_images.parquet \
      --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return; }
  $AIC_PY $CONV --out "$OUT/$TAG.jsonl" --offset 250399 --max-requests 749601 \
      --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

run_policy fc_p90_L30_toto     toto    30  &
run_policy fc_p90_L300_toto    toto    300 &
run_policy fc_p90_L30_timesfm  timesfm 30  &
run_policy fc_p90_L300_timesfm timesfm 300 &
wait
echo "model-sensitivity aggregate complete"

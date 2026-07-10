#!/bin/bash
EDA=/home/gio/tese/eda/.venv/bin/python
AIC=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
CONV=/home/gio/tese/workload/trace_to_two_pool.py
SCHED=/home/gio/tese/simulation/forecast_schedule.py
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json
OUT=/home/gio/tese/simulation/results/week_matrix
cell() {  # policy quantile model rho lead
  local POL=$1 Q=$2 M=$3 R=$4 L=$5
  local TAG
  if [ "$POL" = reactive ]; then TAG="react_rho${R}_L${L}"; else TAG="${POL}_${Q}_${M}_rho${R}_L${L}"; fi
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && return
  local PARQ=/home/gio/tese/predictors/results/${M}_images.parquet
  [ "$POL" = reactive ] && PARQ=/home/gio/tese/predictors/results/chronos_images.parquet
  $EDA $SCHED --window aggregate --policy "$POL" --resolution 15s \
    --quantile "$Q" --rho "$R" --cold-start-s "$L" --hysteresis-min 3 \
    --parquet "$PARQ" --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return; }
  $AIC $CONV --out "$OUT/$TAG.jsonl" --offset 250399 --max-requests 749601 \
    --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
    > "$OUT/$TAG.log" 2>&1 && { rm -f "$OUT/$TAG.jsonl"; echo "done $TAG"; } || echo "FAIL $TAG"
}
export -f cell
export EDA AIC CONV SCHED OUT
# build the job list: forecast (p50/p90 x chronos/toto/timesfm) + reactive, x rho{10,15,20,25} x lead{15,30,45,300}
JOBS=$OUT/jobs.txt; : > $JOBS
for R in 10 15 20 25; do for L in 15 30 45 300; do
  for Q in p50 p90; do for M in chronos toto timesfm; do echo "forecast $Q $M $R $L" >> $JOBS; done; done
  echo "reactive p90 chronos $R $L" >> $JOBS
done; done
wc -l $JOBS
# run 20-way parallel
cat $JOBS | xargs -P 20 -L 1 bash -c 'cell "$@"' _ 
echo "week-matrix done $(date -u +%H:%M:%S)" >> $OUT/status.txt

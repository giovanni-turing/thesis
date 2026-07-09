#!/bin/bash
# 4.4 weekly aggregate — THE headline: SLA x provisioned worker-seconds over
# the full 15-s-forecast-covered span (windows.json "aggregate": offset
# 250399, n 749601, 5.60 days, 2024-10-16 21:39 .. trace end), encoder pool.
# 6 policy runs (chronos schedule; rho15, 15s, hyst 3min) + 2 static refs.
set -u
OUT=/home/gio/tese/simulation/results/aggregate44
mkdir -p "$OUT"
EDA_PY=/home/gio/tese/eda/.venv/bin/python
AIC_PY=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
CONV=/home/gio/tese/workload/trace_to_two_pool.py
SCHED=/home/gio/tese/simulation/forecast_schedule.py
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json

run_policy() {  # $1 tag  $2 policy  $3 quantile  $4 lead_s
  local TAG=$1 POL=$2 Q=$3 L=$4
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $EDA_PY $SCHED --window aggregate --policy "$POL" --resolution 15s \
      --quantile "$Q" --rho 15 --cold-start-s "$L" --hysteresis-min 3 \
      --parquet /home/gio/tese/predictors/results/chronos_images.parquet \
      --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return; }
  $AIC_PY $CONV --out "$OUT/$TAG.jsonl" --offset 250399 --max-requests 749601 \
      --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

run_static() {  # $1 tag  $2 workers
  local TAG=$1 C=$2
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $AIC_PY $CONV --out "$OUT/$TAG.jsonl" --offset 250399 --max-requests 749601 \
      --encoder-workers "$C" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

run_policy fc_p90_L30   forecast p90 30  &
run_policy fc_p90_L300  forecast p90 300 &
run_policy fc_p50_L30   forecast p50 30  &
run_policy fc_p50_L300  forecast p50 300 &
run_policy react_L30    reactive p90 30  &
run_policy react_L300   reactive p90 300 &
run_static static_C16 16 &
run_static static_C2   2 &
wait
echo "aggregate complete"
for f in "$OUT"/*.jsonl.stats.json; do
  python3 -c "
import json; st=json.load(open('$f'))
ws=st.get('provisioned_worker_seconds') or st['encoder_workers']*st['sim_horizon_s']
print('$f'.split('/')[-1].replace('.jsonl.stats.json',''),
      '| p99', st['encoder_delay_ms']['p99'],
      '| ws', round(ws), '| util', st.get('encoder_utilization'))"
done

#!/bin/bash
# 4.4 riders (local, LLM pool, source build, TP2 on burst1):
#  (c) reactive planner tightened-targets ladder at startup_time=60 s —
#      "reactive can pass the tail SLA only by spending": sweep window-mean
#      targets down until tail passes, record replicas/GPU-time. Config =
#      3.2 variant-B shape (sla target, both loops, ARIMA) on the composed
#      C* trace, plus mocker-native worker cold start.
#  (lead) forecast closed loop re-run under realistic LLM leads
#      startup_time in {60,90,120,300} s — same config as the ledgered
#      fc_burst1_tp2_s8 (identical trace/scale/T0), lead added.
set -u
OUT=/home/gio/tese/simulation/results/riders44
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
GRID_TRACE=/home/gio/tese/simulation/results/grid/traces/grid_burst1_C6.jsonl
FC_TRACE=/home/gio/tese/simulation/results/sweeps/traces/llm_burst1.jsonl

# --- (c) target ladder: ttft/itl window-mean targets, tail graded 1000/100 ---
for T in "400 40" "300 30" "250 25" "200 20"; do
  set -- $T
  TAG="ladder_t${1}_${2}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; continue; }
  cat > "$OUT/planner_$TAG.json" <<EOF
{"mode":"agg","environment":"virtual","namespace":"l44_${1}","backend":"vllm",
 "optimization_target":"sla","ttft_ms":${1}.0,"itl_ms":${2}.0,
 "enable_throughput_scaling":true,"enable_load_scaling":true,
 "load_predictor":"arima","throughput_adjustment_interval_seconds":60,
 "load_adjustment_interval_seconds":15,
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1}
EOF
  (
    RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash $RR "$GRID_TRACE" aic "$OUT/$TAG.report.json" 2 \
      --planner-config "$OUT/planner_$TAG.json" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
  ) &
done

# --- (lead) forecast closed loop under LLM startup_time ---
for L in 60 90 120 300; do
  TAG="fc_lead${L}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; continue; }
  (
    RUST_LOG=warn FORECAST_REQ_SCALE=8.0 AIC_TP=2 STARTUP_TIME=$L \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
    FORECAST_T0="2024-10-21 12:59:00" \
    bash $RR "$FC_TRACE" aic "$OUT/$TAG.report.json" 2 \
      --planner-config /home/gio/tese/simulation/planner_forecast_smoke.json \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
  ) &
done
wait
echo "riders complete"
for f in /home/gio/tese/simulation/results/riders44/*.report.json; do
  python3 -c "
import json,sys
r=json.load(open('$f'))
print('$f'.split('/')[-1], '| ttft p99', round(r.get('p99_ttft_ms',-1),1),
      '| itl p99', round(r.get('p99_itl_ms',-1),2))" 2>/dev/null
done

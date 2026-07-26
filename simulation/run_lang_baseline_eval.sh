#!/bin/bash
# Held-out eval of the 1.4-day-calibrated baselines: reactive (200/20, the tightest =
# calib-selected among all-failing) and static TP2x2 (calib-confirmed minimal-feasible),
# on the eval-span bursts. Completes the symmetric 3-arm comparison vs the forecast
# operating point. Week baselines already exist (llm_week/week_re, static 537.4 GPU-h).
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep/baseline_eval
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TD=/home/gio/tese/simulation/results/grid/traces
declare -A TR=( [burst1]=grid_burst1_C6 [burst3]=grid_burst3_C7 [burst4]=grid_burst4_C7 [burst5]=grid_burst5_C8 )
MAXJOBS=4

react(){ local W=$1; local TAG="react_${W}_t200_20"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  cat > "$OUT/cfg_$TAG.json" <<EOF
{"mode":"agg","environment":"virtual","namespace":"be_${W}","backend":"vllm",
 "optimization_target":"sla","ttft_ms":200.0,"itl_ms":20.0,
 "enable_throughput_scaling":true,"enable_load_scaling":true,"load_predictor":"arima",
 "throughput_adjustment_interval_seconds":60,"load_adjustment_interval_seconds":15,
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1}
EOF
  RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TD/${TR[$W]}.jsonl" aic "$OUT/$TAG.report.json" 2 \
      --planner-config "$OUT/cfg_$TAG.json" > "$OUT/$TAG.log" 2>&1 \
    && echo "done $TAG" || echo "FAIL $TAG"
}
static(){ local W=$1; local TAG="static_${W}_tp2x2"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  RUST_LOG=warn AIC_TP=2 STARTUP_TIME=0 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TD/${TR[$W]}.jsonl" aic "$OUT/$TAG.report.json" 2 \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}
for W in burst1 burst3 burst4 burst5; do
  react "$W" & static "$W" &
  while [ "$(jobs -rp|wc -l)" -ge $MAXJOBS ]; do sleep 2; done
done
wait
echo "=== baseline held-out eval (reactive 200/20 + static TP2x2 on eval bursts) complete ==="

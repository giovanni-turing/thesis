#!/bin/bash
# Prove the reactive baseline's failure is PREDICTOR-INDEPENDENT: run the shipped Dynamo
# planner (200/20 targets, both loops) with load_predictor in {constant,kalman,prophet}
# (arima already covered by baseline_eval) held-out on the eval bursts. 'constant' is the
# genuinely forecast-FREE reactive point. If all fail alike -> neither ARIMA nor
# forecasting-vs-not decides it; the mean conversion does.
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep/baseline_eval
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TD=/home/gio/tese/simulation/results/grid/traces
declare -A TR=( [burst1]=grid_burst1_C6 [burst3]=grid_burst3_C7 [burst4]=grid_burst4_C7 [burst5]=grid_burst5_C8 )
MAXJOBS=4
one(){ local W=$1 P=$2; local TAG="react_${W}_pred_${P}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  cat > "$OUT/cfg_$TAG.json" <<EOF
{"mode":"agg","environment":"virtual","namespace":"ps_${W}_${P}","backend":"vllm",
 "optimization_target":"sla","ttft_ms":200.0,"itl_ms":20.0,
 "enable_throughput_scaling":true,"enable_load_scaling":true,"load_predictor":"${P}",
 "throughput_adjustment_interval_seconds":60,"load_adjustment_interval_seconds":15,
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1}
EOF
  RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TD/${TR[$W]}.jsonl" aic "$OUT/$TAG.report.json" 2 \
      --planner-config "$OUT/cfg_$TAG.json" > "$OUT/$TAG.log" 2>&1 \
    && echo "done $TAG" || echo "FAIL $TAG"
}
for P in constant kalman prophet; do
  for W in burst1 burst3 burst4 burst5; do
    one "$W" "$P" &
    while [ "$(jobs -rp|wc -l)" -ge $MAXJOBS ]; do sleep 2; done
  done
done
wait
echo "=== reactive predictor sweep (constant/kalman/prophet on eval bursts) complete ==="

#!/bin/bash
# Symmetric held-out baselines: calibrate the REACTIVE planner targets AND the STATIC
# TP shape on the 1.4-day split (burst2+burst6) only -- so all three arms (forecast,
# reactive, static) are calibrated on the same data. Reactive = Dynamo SLA planner
# (variant B: optimization_target=sla, ARIMA), target ladder {400/40,300/30,250/25,
# 200/20}. Static = fixed TPxN, no planner (TP1x4 iso-cost vs TP2x2). Composed C*
# traces (grid_burst2_C8 / grid_burst6_C6), TP2 engine, 60s lead. Held-out eval is a
# separate step (run_lang_baseline_eval.sh) once the calib winner is picked.
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep/baseline_calib
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TD=/home/gio/tese/simulation/results/grid/traces
declare -A TR=( [burst2]=grid_burst2_C8 [burst6]=grid_burst6_C6 )
MAXJOBS=4

react(){ # window t1 t2
  local W=$1 T1=$2 T2=$3
  local TAG="react_${W}_t${T1}_${T2}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  cat > "$OUT/cfg_$TAG.json" <<EOF
{"mode":"agg","environment":"virtual","namespace":"bc_${W}_${T1}_${T2}","backend":"vllm",
 "optimization_target":"sla","ttft_ms":${T1}.0,"itl_ms":${T2}.0,
 "enable_throughput_scaling":true,"enable_load_scaling":true,"load_predictor":"arima",
 "throughput_adjustment_interval_seconds":60,"load_adjustment_interval_seconds":15,
 "advisory":true,"max_gpu_budget":8,"min_endpoint":1}
EOF
  RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TD/${TR[$W]}.jsonl" aic "$OUT/$TAG.report.json" 2 \
      --planner-config "$OUT/cfg_$TAG.json" > "$OUT/$TAG.log" 2>&1 \
    && echo "done $TAG" || echo "FAIL $TAG"
}

static(){ # window tp n
  local W=$1 TP=$2 N=$3
  local TAG="static_${W}_tp${TP}x${N}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  RUST_LOG=warn AIC_TP=$TP STARTUP_TIME=0 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash "$RR" "$TD/${TR[$W]}.jsonl" aic "$OUT/$TAG.report.json" $N \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

for W in burst2 burst6; do
  for T in "400 40" "300 30" "250 25" "200 20"; do
    set -- $T; react "$W" "$1" "$2" &
    while [ "$(jobs -rp|wc -l)" -ge $MAXJOBS ]; do sleep 2; done
  done
  static "$W" 1 4 &   # TP1x4 (iso-cost 4 GPUs; expect prefill-floor FAIL)
  static "$W" 2 2 &   # TP2x2 (expect minimal-feasible)
  while [ "$(jobs -rp|wc -l)" -ge $MAXJOBS ]; do sleep 2; done
done
wait
echo "=== baseline calibration on burst2+burst6 complete ==="

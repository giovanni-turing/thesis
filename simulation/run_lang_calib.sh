#!/bin/bash
# Language-pool quantile x conversion-scale calibration on the 1.4-day split.
#
# Gap closed: the published language policy fixes the forecast quantile at p90
# and derives the tail-aware conversion scale (FORECAST_REQ_SCALE) from r_tail
# measured on burst1/burst4 -- both in the EVAL span. This selects the operating
# point HONESTLY: sweep (quantile x scale) on burst2 + burst6, which both fall
# inside the first 1.4 days (the forecast-context / calibration split) and are
# forecastable via the EXPANDING-CONTEXT archive (*_expctx.parquet, first bin
# 2024-10-15 12:03, vs the fixed-context archive's 2024-10-16 21:39). burst6 is
# a 1-min onset -> the fast-onset stressor lives in the calibration split.
# Pick the cheapest (quantile,scale) passing the tail SLA on BOTH; evaluate that
# point held-out on burst1/3/4/5 + week (run_lang_calib_eval.sh) using the
# production fixed-context archive.
#
# Tail SLA (graded): TTFT p99 < 1000 ms AND ITL p99 < 100 ms. Language pool only
# (encoder priced separately). Composed C* trace per window so the encoder is
# not the bottleneck (clean language isolation). TP2, 2 workers, 60 s lead.
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TRACEDIR=/home/gio/tese/simulation/results/grid/traces
declare -A TRACE=( [burst2]=grid_burst2_C8 [burst6]=grid_burst6_C6 )
declare -A T0=( [burst2]="2024-10-15 21:16:00" [burst6]="2024-10-15 23:26:00" )
QUANTILES="${QUANTILES:-p50 p60 p70 p80 p90}"
SCALES="${SCALES:-2 4 6 8}"
MAXJOBS=5

run_one(){
  local W=$1 Q=$2 S=$3
  local TAG="${W}_${Q}_s${S}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  local NS="lc_${W}_${Q}_${S}"
  cat > "$OUT/cfg_$TAG.json" <<EOF
{"mode":"agg","environment":"virtual","namespace":"$NS","backend":"vllm",
 "ttft_ms":500.0,"itl_ms":50.0,"load_predictor":"forecast_file",
 "enable_throughput_scaling":true,"enable_load_scaling":false,
 "throughput_adjustment_interval_seconds":60,"max_gpu_budget":8,
 "min_endpoint":1,"advisory":true,"optimization_target":"sla"}
EOF
  RUST_LOG=warn FORECAST_REQ_SCALE=$S AIC_TP=2 STARTUP_TIME=60 \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
    FORECAST_MODEL=chronos FORECAST_SUFFIX=_expctx FORECAST_RESOLUTION=15s \
    FORECAST_QUANTILE=$Q FORECAST_T0="${T0[$W]}" \
    bash "$RR" "$TRACEDIR/${TRACE[$W]}.jsonl" aic "$OUT/$TAG.report.json" 2 \
      --planner-config "$OUT/cfg_$TAG.json" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

for W in burst2 burst6; do
  for Q in $QUANTILES; do
    for S in $SCALES; do
      run_one "$W" "$Q" "$S" &
      while [ "$(jobs -rp | wc -l)" -ge "$MAXJOBS" ]; do sleep 2; done
    done
  done
done
wait
echo "=== calibration sweep complete ==="

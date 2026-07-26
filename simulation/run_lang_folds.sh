#!/bin/bash
# Language fold-invariance at the calibrated p70/s6 operating point.
# Reuses the g4 per-fold composed traces (defense/anim/data/g4_folds/F*_enc_fc_rho15.jsonl,
# fixed rho15 encoder schedule), the same expanding-context archive, and the same static
# denominator (F*_lang_static.report.json, ~96 GPU-h/fold = TP2x2) the published p90/s8
# fold analysis used -- so the ONLY change is language quantile p90->p70, scale 8->6.
# Answers: does the ~0.62x language cost hold across the 7 disjoint 24-h folds, or is it a
# span-average like the encoder's 0.47-1.10x (and does p70/s6 beat p90/s8's 0.93-3.81x)?
set -u
Q="${Q:-p70}"; S="${S:-6}"
OUT=/home/gio/tese/simulation/results/lang_qsweep/folds_${Q}_s${S}
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
GD=/home/gio/tese/defense/anim/data/g4_folds
declare -A T0=( [F1]="2024-10-15 12:03:00" [F2]="2024-10-16 12:00:00" [F3]="2024-10-17 12:00:00" \
                [F4]="2024-10-18 12:00:00" [F5]="2024-10-19 12:00:00" [F6]="2024-10-20 12:00:00" \
                [F7]="2024-10-21 12:00:00" )
MAXJOBS=5
one(){
  local F=$1 TAG="${1}_lang_${Q}_s${S}"
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  local CFG="$OUT/cfg_$TAG.json"
  cat > "$CFG" <<EOF
{"mode":"agg","environment":"virtual","namespace":"lf_${F}_${Q}_${S}","backend":"vllm",
 "ttft_ms":500.0,"itl_ms":50.0,"load_predictor":"forecast_file",
 "enable_throughput_scaling":true,"enable_load_scaling":false,
 "throughput_adjustment_interval_seconds":60,"max_gpu_budget":8,
 "min_endpoint":1,"advisory":true,"optimization_target":"sla"}
EOF
  RUST_LOG=warn FORECAST_REQ_SCALE=$S AIC_TP=2 STARTUP_TIME=60 \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
    FORECAST_MODEL=chronos FORECAST_SUFFIX=_expctx FORECAST_RESOLUTION=15s \
    FORECAST_QUANTILE=$Q FORECAST_T0="${T0[$F]}" \
    bash "$RR" "$GD/${F}_enc_fc_rho15.jsonl" aic "$OUT/$TAG.report.json" 2 \
      --planner-config "$CFG" > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}
for F in ${FOLDS:-F1 F2 F3 F4 F5 F6 F7}; do
  one "$F" &
  while [ "$(jobs -rp | wc -l)" -ge "$MAXJOBS" ]; do sleep 2; done
done
wait
echo "=== language fold sweep complete for $Q/s$S ==="

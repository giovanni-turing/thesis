#!/bin/bash
# Held-out evaluation of the calibration-selected language operating point.
# EVAL_Q (e.g. p70) + EVAL_S (e.g. 6) = the (quantile,scale) picked on burst2+burst6
# by run_lang_calib.sh. Evaluate on the EVAL span (burst1/3/4/5 + week) using the
# PRODUCTION fixed-context archive (NO _expctx) -- every eval window is after the
# 2024-10-16 21:39 calibration boundary, so the standard archive covers them, and
# this matches the thesis's published language numbers exactly.
# Compare vs the published p90/scale8 point (week_fc_p90: 651 ms / 518.6 GPU-h).
set -u
: "${EVAL_Q:?set EVAL_Q e.g. p70}"; : "${EVAL_S:?set EVAL_S e.g. 6}"
MODE="${MODE:-all}"   # bursts | week | all
OUT=/home/gio/tese/simulation/results/lang_qsweep/eval_${EVAL_Q}_s${EVAL_S}
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TD=/home/gio/tese/simulation/results/grid/traces
CFG="$OUT/cfg.json"
cat > "$CFG" <<EOF
{"mode":"agg","environment":"virtual","namespace":"leval_${EVAL_Q}_${EVAL_S}","backend":"vllm",
 "ttft_ms":500.0,"itl_ms":50.0,"load_predictor":"forecast_file",
 "enable_throughput_scaling":true,"enable_load_scaling":false,
 "throughput_adjustment_interval_seconds":60,"max_gpu_budget":8,
 "min_endpoint":1,"advisory":true,"optimization_target":"sla"}
EOF
run(){ # name trace T0
  local NAME=$1 TRACE=$2 T0=$3
  [ -f "$OUT/$NAME.report.json" ] && { echo "skip $NAME"; return; }
  RUST_LOG=warn FORECAST_REQ_SCALE=$EVAL_S AIC_TP=2 STARTUP_TIME=60 \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
    FORECAST_MODEL=chronos FORECAST_RESOLUTION=15s FORECAST_QUANTILE=$EVAL_Q \
    FORECAST_T0="$T0" \
    bash "$RR" "$TRACE" aic "$OUT/$NAME.report.json" 2 --planner-config "$CFG" \
      > "$OUT/$NAME.log" 2>&1 && echo "done $NAME" || echo "FAIL $NAME"
}
if [ "$MODE" != week ]; then
  run burst1 "$TD/grid_burst1_C6.jsonl" "2024-10-21 12:59:00" &
  run burst3 "$TD/grid_burst3_C7.jsonl" "2024-10-18 10:18:00" &
  run burst4 "$TD/grid_burst4_C7.jsonl" "2024-10-18 15:37:00" &
  run burst5 "$TD/grid_burst5_C8.jsonl" "2024-10-18 14:32:00" &
  wait
fi
if [ "$MODE" != bursts ]; then
  run week /home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl "2024-10-16 21:39:00"
fi
echo "=== eval complete for $EVAL_Q / s$EVAL_S ==="

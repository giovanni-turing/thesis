#!/bin/bash
# Completeness week runs: (1) Chronos p90 + MEAN conversion (scale=1) on the full week ->
# conversion-lever result at week scale; (2) the e13-robust point p90/s6 with Toto and
# TimesFM -> model-independence of the 0.82x. All on the aggregate composed trace, standard
# archive, T0=eval boundary. CPU-only. Parallel.
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep/extra_week
mkdir -p "$OUT"
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
TRACE=/home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl
CFG=/home/gio/tese/simulation/planner_forecast_smoke.json
run(){ # tag model quantile scale
  local TAG=$1 M=$2 Q=$3 S=$4
  [ -f "$OUT/$TAG.report.json" ] && { echo "skip $TAG"; return; }
  RUST_LOG=warn FORECAST_REQ_SCALE=$S AIC_TP=2 STARTUP_TIME=60 \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
    FORECAST_MODEL=$M FORECAST_RESOLUTION=15s FORECAST_QUANTILE=$Q \
    FORECAST_T0="2024-10-16 21:39:00" \
    bash "$RR" "$TRACE" aic "$OUT/$TAG.report.json" 2 --planner-config "$CFG" \
      > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}
run week_chronos_p90_s1_meanconv chronos p90 1 &   # (1) TSFM + mean conversion @ week
run week_toto_p90_s6            toto    p90 6 &     # (2) robust point, Toto
run week_timesfm_p90_s6         timesfm p90 6 &     # (2) robust point, TimesFM
wait
echo "=== extra week runs complete ==="

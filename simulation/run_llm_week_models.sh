#!/bin/bash
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python; TRACE=/home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl; OUT=/home/gio/tese/simulation/results/llm_week
for M in toto timesfm; do
  [ -f "$OUT/week_fc_p90_$M.report.json" ] && { echo "skip $M"; continue; }
  RUST_LOG=warn FORECAST_REQ_SCALE=8.0 AIC_TP=2 STARTUP_TIME=60 \
  REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
  REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
  FORECAST_T0="2024-10-16 21:39:00" FORECAST_RESOLUTION=15s \
  FORECAST_MODEL=$M FORECAST_QUANTILE=p90 \
  bash /home/gio/tese/simulation/run_replay.sh "$TRACE" aic "$OUT/week_fc_p90_$M.report.json" 2 \
    --planner-config /home/gio/tese/simulation/planner_forecast_smoke.json \
    > "$OUT/week_fc_p90_$M.log" 2>&1
  echo "week-$M rc=$? $(date -u +%H:%M:%S)" >> "$OUT/status.txt"
done
echo "llm-week-models done" >> "$OUT/status.txt"

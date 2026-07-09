#!/usr/bin/env bash
# Full-week LLM closed-loop replays (fc-p90 + reactive), detached.
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
TRACE=/home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl
OUT=/home/gio/tese/simulation/results/llm_week
cd /home/gio/tese/simulation
(
  RUST_LOG=warn FORECAST_REQ_SCALE=8.0 AIC_TP=2 STARTUP_TIME=60 \
  REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
  REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
  FORECAST_T0="2024-10-16 21:39:00" FORECAST_RESOLUTION=15s \
  FORECAST_MODEL=chronos FORECAST_QUANTILE=p90 \
  bash run_replay.sh "$TRACE" aic "$OUT/week_fc_p90.report.json" 2 \
    --planner-config /home/gio/tese/simulation/planner_forecast_smoke.json \
    > "$OUT/week_fc_p90.log" 2>&1; echo "fc rc=$?" >> "$OUT/status.txt"
) &
(
  RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
  bash run_replay.sh "$TRACE" aic "$OUT/week_re.report.json" 2 \
    --planner-config /home/gio/tese/simulation/results/riders44/planner_ladder_t200_20.json \
    > "$OUT/week_re.log" 2>&1; echo "re rc=$?" >> "$OUT/status.txt"
) &
wait
echo "all done $(date -u +%H:%M:%S)" >> "$OUT/status.txt"

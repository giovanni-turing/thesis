#!/bin/bash
RUST_LOG=warn FORECAST_REQ_SCALE=8.0 AIC_TP=2 STARTUP_TIME=60 \
REPLAY_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python AIC_VER=0.19.0 \
REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
FORECAST_T0="2024-10-16 21:39:00" FORECAST_RESOLUTION=15s \
FORECAST_MODEL=chronos FORECAST_QUANTILE=p50 \
bash /home/gio/tese/simulation/run_replay.sh "/home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl" aic "/home/gio/tese/simulation/results/llm_week/week_fc_p50.report.json" 2 \
  --planner-config /home/gio/tese/simulation/planner_forecast_smoke.json \
  > "/home/gio/tese/simulation/results/llm_week/week_fc_p50.log" 2>&1
echo "llm-week-p50 rc=$? $(date -u +%H:%M:%S)" >> "/home/gio/tese/simulation/results/llm_week/status.txt"
# cleanup the big regenerated trace after (it's an input, regenerable)

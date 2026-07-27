#!/bin/bash
# Stage L6/L7: steady24h planner arms on the EXISTING composed traces
# (defense/anim/data/a2_runs/steady24h_{forecast,reactive}_L30.jsonl).
# L6 = forecast-p90 chronos (replay_with_forecast.py + forecast smoke planner)
# L7 = reactive (ARIMA ladder t200/20), exactly as gen_a6_runs.py / gen_a12_e2e.py.
set -u
ROOT=/home/gio/tese
OUT=$ROOT/simulation/results/composed_fill
export RUST_LOG=warn AIC_TP=2 AIC_VER=0.19.0 STARTUP_TIME=60
export REPLAY_PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python

l6() {
  REPLAY_ENTRY=$ROOT/simulation/replay_with_forecast.py \
  FORECAST_T0="2024-10-19 00:00:00" FORECAST_MODEL=chronos FORECAST_QUANTILE=p90 \
  FORECAST_RESOLUTION=15s FORECAST_REQ_SCALE=8.0 \
  bash $ROOT/simulation/run_replay.sh \
    $ROOT/defense/anim/data/a2_runs/steady24h_forecast_L30.jsonl aic \
    $OUT/steady24h_fc_chronos.report.json 2 \
    --planner-config $ROOT/simulation/planner_forecast_smoke.json \
    --report-jsonl $OUT/steady24h_fc_chronos.requests.jsonl \
    > $OUT/steady24h_fc_chronos.log 2>&1
  echo "l6 rc=$?"
}

l7() {
  bash $ROOT/simulation/run_replay.sh \
    $ROOT/defense/anim/data/a2_runs/steady24h_reactive_L30.jsonl aic \
    $OUT/steady24h_reactive.report.json 2 \
    --planner-config $ROOT/simulation/results/riders44/planner_ladder_t200_20.json \
    --report-jsonl $OUT/steady24h_reactive.requests.jsonl \
    > $OUT/steady24h_reactive.log 2>&1
  echo "l7 rc=$?"
}

l6 &
l7 &
wait
echo STAGE_L_PLANNER_DONE

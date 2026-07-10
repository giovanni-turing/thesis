#!/bin/bash
SRC_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
OUT=/home/gio/tese/simulation/results/episode_twins
mkdir -p $OUT
cd /home/gio/tese/simulation
RR=/home/gio/tese/simulation/run_replay.sh
FCFG=/home/gio/tese/simulation/planner_forecast_smoke.json
RCFG=/home/gio/tese/simulation/results/riders44/planner_ladder_t200_20.json
declare -A T0=( [burst1]="2024-10-21 12:59:00" [burst4]="2024-10-18 15:37:00" [burst5]="2024-10-18 14:32:00" )
declare -A TR=( [burst1]=grid_burst1_C6 [burst4]=grid_burst4_C7 [burst5]=grid_burst5_C8 )
for W in burst1 burst4 burst5; do
  TRACE=/home/gio/tese/simulation/results/grid/traces/${TR[$W]}.jsonl
  # forecast p90
  ( [ -f "$OUT/${W}_fc.report.json" ] || RUST_LOG=warn FORECAST_REQ_SCALE=8.0 AIC_TP=2 STARTUP_TIME=60 \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 REPLAY_ENTRY=/home/gio/tese/simulation/replay_with_forecast.py \
    FORECAST_T0="${T0[$W]}" FORECAST_RESOLUTION=15s FORECAST_MODEL=chronos FORECAST_QUANTILE=p90 \
    bash $RR "$TRACE" aic "$OUT/${W}_fc.report.json" 2 --planner-config $FCFG \
    > "$OUT/${W}_fc.log" 2>&1; echo "fc $W rc=$?" >> $OUT/status.txt ) &
  # reactive
  ( [ -f "$OUT/${W}_re.report.json" ] || RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 \
    REPLAY_PY=$SRC_PY AIC_VER=0.19.0 \
    bash $RR "$TRACE" aic "$OUT/${W}_re.report.json" 2 --planner-config $RCFG \
    > "$OUT/${W}_re.log" 2>&1; echo "re $W rc=$?" >> $OUT/status.txt ) &
done
wait
echo "episode-twins done $(date -u +%H:%M:%S)" >> $OUT/status.txt

#!/bin/bash
# Stage L1-L5: language-pool replays of the static-C8 composed traces.
# No planner (static arm), 2 workers, aic timing — same run_replay.sh invocation
# as gen_a13_fulltrace.py llm(planner=False).
set -u
ROOT=/home/gio/tese
OUT=$ROOT/simulation/results/composed_fill
export RUST_LOG=warn AIC_TP=2 AIC_VER=0.19.0 STARTUP_TIME=60
export REPLAY_PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python

run() {
  W=$1
  bash $ROOT/simulation/run_replay.sh $OUT/${W}_static_C8.jsonl aic \
    $OUT/${W}_static.report.json 2 \
    --report-jsonl $OUT/${W}_static.requests.jsonl > $OUT/${W}_static.log 2>&1
  echo "$W rc=$?"
}

run burst3 &
run burst5 &
run burst4 &
run burst1 &
wait
run steady24h
echo STAGE_L_STATIC_DONE

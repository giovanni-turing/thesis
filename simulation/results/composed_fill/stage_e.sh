#!/bin/bash
# Stage E: composed static-C8 encoder conversions for the 5 fill windows.
# Convention: bare --encoder-workers 8, NO --worker-schedule (gen_a6_runs.py:70-73,
# gen_a13_fulltrace.py:44-49), under the snapshot shim.
set -u
ROOT=/home/gio/tese
AIC_PY=$ROOT/ai-dynamo/aiconfigurator/.venv/bin/python
OUT=$ROOT/simulation/results/composed_fill
export TESE_ROOT=$ROOT TESE_WINDOWS=$ROOT/simulation/windows.json

run() {
  W=$1; OFFSET=$2; N=$3
  /usr/bin/time -v -o $OUT/${W}_static_C8.time \
  $AIC_PY $ROOT/defense/anim/build/a2_conv_snapshot.py \
    --out $OUT/${W}_static_C8.jsonl --offset $OFFSET --max-requests $N \
    --encoder-workers 8 --series-out $OUT/${W}_static_C8.series.json \
    > $OUT/${W}_static_C8.conv.log 2>&1
  echo "$W rc=$?"
}

run burst1 843072 64804 &
run burst3 531966 3093 &
run burst4 565664 25639 &
run burst5 558386 8983 &
wait
run steady24h 627019 88260
echo STAGE_E_DONE

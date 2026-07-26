#!/bin/bash
set -euo pipefail
ROOT=/home/gio/tese; SP=/tmp/claude-1000/-home-gio-tese/536c024f-0628-41c2-a733-5cb1f35b7714/scratchpad
OUT=$ROOT/simulation/results/comparator_frontier/adversarial; mkdir -p "$OUT"
PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python; CONV=$ROOT/workload/trace_to_two_pool.py
WIN=$ROOT/simulation/windows.json; export TESE_WINDOWS=$WIN TESE_ROOT=$ROOT
off(){ $PY -c "import json;print(json.load(open('$WIN'))['$1']['offset'])"; }
nreq(){ $PY -c "import json;w=json.load(open('$WIN'))['$1'];print(w.get('max_requests') or w.get('requests'))"; }
cell(){
  local W=$1
  local M=$2
  local TAG="${W}_reWPm${M}"
  local OFF NR
  OFF=$(off "$W"); NR=$(nreq "$W")
  $PY $SP/reactive_warmpool.py --window "$W" --resolution 15s --rho 15 --cold-start-s 30 \
      --hysteresis-min 3 --min-workers "$M" --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1
  $PY "$CONV" --out "$OUT/$TAG.jsonl" --offset "$OFF" --max-requests "$NR" --encoder-workers 2 \
      --worker-schedule "$OUT/$TAG.sched.json" > "$OUT/$TAG.conv.log" 2>&1
  echo "done $TAG"; }
export -f cell off nreq; export PY CONV WIN OUT ROOT SP TESE_WINDOWS TESE_ROOT
for W in aggregate burst1 burst3 burst4 burst5 steady24h; do for M in 2 3; do echo "$W $M"; done; done \
  | xargs -P 6 -L1 bash -c 'cell "$0" "$1"'
echo ALLDONE

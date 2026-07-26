#!/bin/bash
set -euo pipefail
ROOT=/home/gio/tese; OUT=$ROOT/simulation/results/comparator_frontier/adversarial
PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python; CONV=$ROOT/workload/trace_to_two_pool.py
GEN=$ROOT/verification/scripts/forecast_schedule_issuetime.py
WIN=$ROOT/simulation/windows.json; export TESE_WINDOWS=$WIN TESE_ROOT=$ROOT
off(){ $PY -c "import json;print(json.load(open('$WIN'))['$1']['offset'])"; }
nreq(){ $PY -c "import json;w=json.load(open('$WIN'))['$1'];print(w.get('max_requests') or w.get('requests'))"; }
cell(){
  local W=$1
  local TAG="${W}_fcSTRICT"
  local OFF NR
  OFF=$(off "$W"); NR=$(nreq "$W")
  $PY "$GEN" --window "$W" --quantile p90 --rho 15 --cold-start-s 30 --hysteresis-min 3 \
      --strict-rewarm --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1
  $PY "$CONV" --out "$OUT/$TAG.jsonl" --offset "$OFF" --max-requests "$NR" --encoder-workers 2 \
      --worker-schedule "$OUT/$TAG.sched.json" > "$OUT/$TAG.conv.log" 2>&1
  echo "done $TAG"; }
export -f cell off nreq; export PY CONV GEN WIN OUT ROOT TESE_WINDOWS TESE_ROOT
for W in aggregate burst1 burst3 burst4 burst5 steady24h; do echo "$W"; done | xargs -P 6 -L1 bash -c 'cell "$0"'
echo ALLDONE

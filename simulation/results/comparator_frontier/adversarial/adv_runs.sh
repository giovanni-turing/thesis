#!/bin/bash
set -euo pipefail
ROOT=/home/gio/tese
SP=/tmp/claude-1000/-home-gio-tese/536c024f-0628-41c2-a733-5cb1f35b7714/scratchpad
OUT=$ROOT/simulation/results/comparator_frontier/adversarial
mkdir -p "$OUT"
PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python
CONV=$ROOT/workload/trace_to_two_pool.py
WIN=$ROOT/simulation/windows.json
export TESE_WINDOWS=$WIN
RHO=15; L=30; RES=15s
off()  { $PY -c "import json;print(json.load(open('$WIN'))['$1']['offset'])"; }
nreq() { $PY -c "import json;w=json.load(open('$WIN'))['$1'];print(w.get('max_requests') or w.get('requests'))"; }
cell() { # $1 window $2 variant
  local W=$1 V=$2 GEN H TAG OFF NR
  case "$V" in
    oracleH3)  GEN=$ROOT/simulation/comparator_frontier_oracle.py; H=3; TAG="${W}_oracleH3" ;;
    oracleWS)  GEN=$SP/oracle_warmstart.py;                        H=0; TAG="${W}_oracleWS" ;;
    oracleWSH3)GEN=$SP/oracle_warmstart.py;                        H=3; TAG="${W}_oracleWSH3" ;;
  esac
  OFF=$(off "$W"); NR=$(nreq "$W")
  $PY "$GEN" --window "$W" --resolution "$RES" --rho "$RHO" --cold-start-s "$L" \
      --hysteresis-min "$H" --out "$OUT/$TAG.sched.json" --ledger-out "$OUT/$TAG.ledger.json" \
      > "$OUT/$TAG.sched.log" 2>&1
  $PY "$CONV" --out "$OUT/$TAG.jsonl" --offset "$OFF" --max-requests "$NR" \
      --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" > "$OUT/$TAG.conv.log" 2>&1
  echo "done $TAG"
}
export TESE_ROOT=/home/gio/tese
export -f cell off nreq; export PY CONV WIN OUT RHO L RES ROOT SP TESE_ROOT
export TESE_ROOT=/home/gio/tese
for W in aggregate burst1 burst3 burst4 burst5 steady24h; do
  for V in oracleWS oracleWSH3; do echo "$W $V"; done
done | xargs -P 6 -L1 bash -c 'cell "$0" "$1"'
echo ALLDONE

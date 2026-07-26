#!/bin/bash
# §8.2 decisive-baseline experiment -- THE SINGLE EVALUATION RUN.
#
# !! Every parameter below is FROZEN by simulation/comparator_frontier_calibrate.sh
# !! on the trace's first 1.4 days (burst2/burst6). Nothing in this script may be
# !! tuned after reading its output. Run it ONCE.
#
# Evaluation span (tex/closedloop.tex:43-47): the 5.60-day forecast-covered
# aggregate window, plus its in-span episodes burst1/burst3/burst4/burst5 and the
# calm day steady24h. burst2/burst6 are the CALIBRATION split and are absent here
# by construction.
#
# Five arms, ONE set of mechanics (rho=15 img/s, 15-s control bin, 3-min
# scale-down hysteresis, cold-start lead L=30 s, converter replay through
# --worker-schedule so even the static fleet takes the identical code path):
#   1 fc      forecast p90, issue-time actuation  (existing, unmodified)
#   2 re      same-image-signal reactive, point rate  (existing, unmodified)
#   3 floor   arm 2 + minimum standing worker floor M  (frozen: see FLOOR_M)
#   4 static  deployable static fleet C=8 (tex/baselines.tex:104-106)
#   5 oracle  perfect-future oracle, headroom-free  (frozen: see ORACLE_H)
# plus FAMILY: the whole warm-floor M grid, reported as the reactive+floor
# family's achievable envelope. The envelope is a REPORTED FAMILY, never a
# selection: no M is chosen from these outputs.
#
# Frozen parameters (comparator_frontier_calibrate.sh output,
# simulation/results/comparator_frontier/calib_summary.txt):
#   FLOOR_M  = 4   rule R2: cheapest floor holding encoder p99 < 1000 ms on BOTH
#                  calibration episodes at EVERY declared lead {15,30,45,300}s.
#                  (rule R1 -- cheapest floor passing at L=30 s only -- returns
#                  M=1, i.e. no floor: the calibration episodes' 48/53-min onsets
#                  never defeat the un-floored reactive policy at L=30 s. Arm 3
#                  at M=1 IS arm 2, so R1 is reported as degenerate and the
#                  frontier carries the R2 floor. Set FLOOR_M=1 to reproduce the
#                  degenerate R1 arm.)
#   ORACLE_H = 0   cheapest of the two mechanically admissible hysteresis
#                  settings {0,3} min passing the gate on both calibration
#                  episodes at L=30 s (H=0: 92,093.7 worker-s, p99 906.6/906.6;
#                  H=3: 225,317.8 worker-s, p99 589.3/589.3).
set -euo pipefail

ROOT=/home/gio/tese
OUT="${OUT_DIR:-$ROOT/simulation/results/comparator_frontier/eval}"
mkdir -p "$OUT"

PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python   # the interpreter of the existing arms
FCGEN=$ROOT/verification/scripts/forecast_schedule_issuetime.py
REGEN=$ROOT/verification/scripts/reactive_quantile_schedule.py
ORACLE=$ROOT/simulation/comparator_frontier_oracle.py
CONV=$ROOT/workload/trace_to_two_pool.py
WIN=$ROOT/simulation/windows.json
export TESE_WINDOWS=$WIN

RHO=15; L=30; HYST=3; RES=15s
FLOOR_M="${FLOOR_M:-4}"
ORACLE_H="${ORACLE_H:-0}"
STATIC_C="${STATIC_C:-8}"
FAMILY_M="${FAMILY_M:-1 2 3 4 5 6 7 8 9 10 12 14 16 20 24 32}"
EVAL_WINDOWS="${EVAL_WINDOWS:-aggregate burst1 burst3 burst4 burst5 steady24h}"
JOBS="${JOBS:-4}"   # the aggregate replay is ~15 GB-free but CPU-heavy; keep modest

off()  { $PY -c "import json;print(json.load(open('$WIN'))['$1']['offset'])"; }
nreq() { $PY -c "import json;w=json.load(open('$WIN'))['$1'];print(w.get('max_requests') or w.get('requests'))"; }

replay() {  # $1 window  $2 tag
  local W=$1 TAG=$2 OFF NR
  OFF=$(off "$W"); NR=$(nreq "$W")
  $PY "$CONV" --out "$OUT/$TAG.jsonl" --offset "$OFF" --max-requests "$NR" \
      --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.conv.log" 2>&1
  [ -s "$OUT/$TAG.jsonl.stats.json" ]
}

cell() {  # $1 arm  $2 window
  local ARM=$1 W=$2 TAG
  case "$ARM" in
    fc)
      TAG="${W}_fc_L${L}"
      $PY "$FCGEN" --window "$W" --quantile p90 --rho "$RHO" --cold-start-s "$L" \
          --hysteresis-min "$HYST" --out "$OUT/$TAG.sched.json" \
          --ledger-out "$OUT/$TAG.ledger.json" > "$OUT/$TAG.sched.log" 2>&1 ;;
    re)
      TAG="${W}_re_L${L}"
      $PY "$REGEN" --window "$W" --mode react_point --resolution "$RES" \
          --rho "$RHO" --cold-start-s "$L" --hysteresis-min "$HYST" \
          --min-workers 1 --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 ;;
    floor*)
      local M=${ARM#floor}
      TAG="${W}_floorM${M}_L${L}"
      $PY "$REGEN" --window "$W" --mode react_point --resolution "$RES" \
          --rho "$RHO" --cold-start-s "$L" --hysteresis-min "$HYST" \
          --min-workers "$M" --out "$OUT/$TAG.sched.json" > "$OUT/$TAG.sched.log" 2>&1 ;;
    static)
      TAG="${W}_staticC${STATIC_C}_L${L}"
      # constant capacity through the identical --worker-schedule path
      echo "[[0, $STATIC_C]]" > "$OUT/$TAG.sched.json" ;;
    oracle)
      TAG="${W}_oracle_L${L}_H${ORACLE_H}"
      $PY "$ORACLE" --window "$W" --resolution "$RES" --rho "$RHO" \
          --cold-start-s "$L" --hysteresis-min "$ORACLE_H" \
          --out "$OUT/$TAG.sched.json" --ledger-out "$OUT/$TAG.ledger.json" \
          > "$OUT/$TAG.sched.log" 2>&1 ;;
    *) echo "unknown arm $ARM" >&2; return 1 ;;
  esac
  replay "$W" "$TAG" || { echo "FAIL $TAG" >&2; return 1; }
  echo "done $TAG"
}
export -f cell replay off nreq
export PY FCGEN REGEN ORACLE CONV WIN OUT RHO L HYST RES ORACLE_H STATIC_C

ARMS="${ARMS_OVERRIDE:-}"
if [ -z "$ARMS" ]; then
  ARMS="fc re floor${FLOOR_M} static oracle"
  for M in $FAMILY_M; do
    case " $ARMS " in *" floor$M "*) ;; *) ARMS="$ARMS floor$M" ;; esac
  done
fi

CELLS=$(mktemp)
for W in $EVAL_WINDOWS; do for A in $ARMS; do echo "$A $W"; done; done > "$CELLS"
echo "== $(wc -l < "$CELLS") evaluation cells (arms: $ARMS), ${JOBS}-way =="
xargs -a "$CELLS" -P "$JOBS" -L1 bash -c 'cell "$0" "$1"' \
  || { echo "=== EVALUATION RUN FAILED ===" >&2; exit 1; }
rm -f "$CELLS"
echo "=== evaluation run complete -> $OUT ==="
echo "now:  $PY $ROOT/simulation/comparator_frontier_summarize.py --mode frontier \\"
echo "        --dir $OUT --cost-window aggregate \\"
echo "        --json-out $ROOT/simulation/results/comparator_frontier/frontier.json"

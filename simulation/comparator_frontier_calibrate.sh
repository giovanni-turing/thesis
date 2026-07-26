#!/bin/bash
# §8.2 decisive-baseline experiment -- CALIBRATION SPLIT ONLY.
#
# Freezes the one free parameter of comparator arm (3) "reactive + calibrated
# minimum warm floor M" on the trace's first 1.4 days, and smoke-runs comparator
# arm (5) "perfect-future oracle" (which has NO free parameter) on the same
# split. NOTHING here touches the 5.60-day evaluation span.
#
# Calibration split (tex/closedloop.tex:43-53): the trace's first 1.4 days are
# forecast CONTEXT, never graded as evaluation results; the two burst episodes
# inside it -- burst2 (onset 48 min) and burst6 (onset 53 min) -- are the
# calibration windows, exactly as the language operating point was calibrated
# (tex/closedloop.tex:340-349).
#
# Declared SLA gate (tex/twopool.tex:185-194, restated tex/baselines.tex:14-17):
#   encoder delay p99 < 1000 ms, taken over ALL requests of the window
#   (text-only requests contribute a zero delay: a user-population tail).
#
# Frozen mechanics, identical to the existing fc/re/hybrid encoder arms
# (simulation/run_encoder_hybrid.sh:19 "RHO=15; L=30"):
#   signal      trailing observed image rate, point (mode=react_point) -> the
#               thesis's same-image-signal reactive policy
#               (tex/baselines.tex:188-197)
#   conversion  workers = ceil(rate / rho), rho = 15 img/s
#   floor       workers never below M  (--min-workers M; the ONLY change)
#   hysteresis  3 min scale-down damping
#   startup     cold-start lead L: up-lead / down-now
#               (simulation/forecast_schedule.py:146-150)
#   bin         15 s
#   replay      workload/trace_to_two_pool.py --encoder-workers 2
#               --worker-schedule ...   (the -2 is inert once a schedule is
#               supplied: capacity comes from the schedule, :283-288)
#
# Sweep: M in $MGRID x L in $LGRID x {burst2, burst6}.
#   * primary selection rule R1 (mandated): cheapest M passing the gate on BOTH
#     calibration episodes at the frontier's frozen lead L=30 s.
#   * disclosed secondary rule R2: cheapest M passing the gate on BOTH
#     calibration episodes at EVERY lead of the thesis's declared encoder lead
#     grid {15,30,45,300} s (simulation/run_burst26_reactive.sh:9,
#     tex/baselines.tex tab:base-react-enc) -- i.e. a floor whose standing
#     capacity, not the lead, carries the onset. Reported because R1 can be
#     degenerate (M=1) whenever the calibration episodes contain no onset fast
#     enough to defeat the un-floored reactive policy at L=30.
# BOTH rules read calibration-split data only.
#
# Interpreter: ai-dynamo/dynamo/.venv -- the SAME python that produced the
# existing fc/re/hybrid arms (run_encoder_hybrid.sh:12-15). The aiconfigurator
# venv is dead and its EncoderCostModel build differs by ~0.16% on the encoder
# delay tail; every comparator-frontier arm must use ONE interpreter.
set -euo pipefail

ROOT=/home/gio/tese
OUT=$ROOT/simulation/results/comparator_frontier/calib
mkdir -p "$OUT"

PY=$ROOT/ai-dynamo/dynamo/.venv/bin/python
REGEN=$ROOT/verification/scripts/reactive_quantile_schedule.py
ORACLE=$ROOT/simulation/comparator_frontier_oracle.py
CONV=$ROOT/workload/trace_to_two_pool.py
WIN=$ROOT/simulation/windows.json
export TESE_WINDOWS=$WIN

RHO=15
HYST=3
RES=15s
MGRID="${MGRID:-1 2 3 4 5 6 7 8 9 10 12 14 16 20 24 32}"
LGRID="${LGRID:-15 30 45 300}"
WINDOWS="${WINDOWS:-burst2 burst6}"
JOBS="${JOBS:-8}"

off() { $PY -c "import json;print(json.load(open('$WIN'))['$1']['offset'])"; }
nreq() { $PY -c "import json;w=json.load(open('$WIN'))['$1'];print(w.get('max_requests') or w.get('requests'))"; }

run_floor_cell() {  # $1 window  $2 M  $3 L
  local W=$1 M=$2 L=$3 TAG
  TAG="${W}_floorM${M}_L${L}"
  local OFF NR
  OFF=$(off "$W"); NR=$(nreq "$W")
  $PY "$REGEN" --window "$W" --mode react_point --resolution "$RES" \
      --rho "$RHO" --cold-start-s "$L" --hysteresis-min "$HYST" \
      --min-workers "$M" --out "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.sched.log" 2>&1 \
    || { echo "FAIL sched $TAG" >&2; return 1; }
  $PY "$CONV" --out "$OUT/$TAG.jsonl" --offset "$OFF" --max-requests "$NR" \
      --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.conv.log" 2>&1 \
    || { echo "FAIL replay $TAG" >&2; return 1; }
  [ -s "$OUT/$TAG.jsonl.stats.json" ] || { echo "FAIL nostats $TAG" >&2; return 1; }
  echo "done $TAG"
}

run_oracle_cell() {  # $1 window  $2 L  $3 hysteresis-min
  local W=$1 L=$2 H=$3 TAG
  TAG="${W}_oracle_L${L}_H${H}"
  local OFF NR
  OFF=$(off "$W"); NR=$(nreq "$W")
  $PY "$ORACLE" --window "$W" --resolution "$RES" --rho "$RHO" \
      --cold-start-s "$L" --hysteresis-min "$H" \
      --out "$OUT/$TAG.sched.json" --ledger-out "$OUT/$TAG.ledger.json" \
      > "$OUT/$TAG.sched.log" 2>&1 \
    || { echo "FAIL sched $TAG" >&2; return 1; }
  $PY "$CONV" --out "$OUT/$TAG.jsonl" --offset "$OFF" --max-requests "$NR" \
      --encoder-workers 2 --worker-schedule "$OUT/$TAG.sched.json" \
      > "$OUT/$TAG.conv.log" 2>&1 \
    || { echo "FAIL replay $TAG" >&2; return 1; }
  echo "done $TAG"
}

export -f run_floor_cell run_oracle_cell off nreq
export PY REGEN ORACLE CONV WIN OUT RHO HYST RES

CELLS=$(mktemp)
for W in $WINDOWS; do
  for L in $LGRID; do
    for M in $MGRID; do echo "floor $W $M $L"; done
    echo "oracle $W $L 3"
    echo "oracle $W $L 0"
  done
done > "$CELLS"

echo "== $(wc -l < "$CELLS") calibration cells, ${JOBS}-way =="
xargs -a "$CELLS" -P "$JOBS" -L1 bash -c '
  case "$0" in
    floor)  run_floor_cell "$1" "$2" "$3" ;;
    oracle) run_oracle_cell "$1" "$2" "$3" ;;
  esac' \
  || { echo "=== CALIBRATION SWEEP FAILED ===" >&2; exit 1; }
rm -f "$CELLS"
echo "=== calibration sweep complete -> $OUT ==="

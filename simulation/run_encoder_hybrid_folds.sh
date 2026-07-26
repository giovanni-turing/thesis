#!/bin/bash
# Per-fold encoder 3-way (forecast / reactive / hybrid=max) across the G4 daily folds F1..F7.
# Identical controllers/settings to the aggregate hybrid: issue-time forecast p90/rho15/L30,
# reactive react_point/rho15/L30, hybrid = pointwise max(forecast, reactive). Establishes which
# folds each PURE policy drops and whether the hybrid catches all of them (no regression + the
# e13/F6 onset). Converter-only (CPU). Folds run in parallel; the 3 arms per fold run in sequence.
#
# Failure semantics: every step is checked explicitly. The ONE tolerated condition is the
# forecast generator's documented refusal "no forecast rows cover window <W>" (true for F1,
# whose window starts before the 15-s forecast archive): the fc arm is then skipped and the
# hybrid degenerates to the reactive schedule via combine_schedules.py --allow-missing, which
# is still replayed as a real hybrid arm. Any other error fails the fold, and any failed fold
# makes the script exit nonzero -- it can no longer print "complete" over missing arms.
set -euo pipefail
OUT=/home/gio/tese/simulation/results/encoder_hybrid/folds
mkdir -p "$OUT"
GENPY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python   # imports aiconfigurator EncoderCostModel
GEN=/home/gio/tese/verification/scripts/forecast_schedule_issuetime.py
REGEN=/home/gio/tese/verification/scripts/reactive_quantile_schedule.py
CONV=/home/gio/tese/workload/trace_to_two_pool.py
COMB=/home/gio/tese/simulation/combine_schedules.py
WIN=/home/gio/tese/simulation/windows.json
RHO=15; L=30
FOLDS="${FOLDS:-F1 F2 F3 F4 F5 F6 F7}"
NO_COVERAGE='no forecast rows cover window'

run_fold(){
  set -euo pipefail
  local W=$1
  local OFF MAX fc_ok tags tag
  OFF=$($GENPY -c "import json;print(json.load(open('$WIN'))['$W']['offset'])")
  MAX=$($GENPY -c "import json;w=json.load(open('$WIN'))['$W'];print(w.get('max_requests') or w.get('requests'))")

  # forecast arm: tolerate ONLY the documented no-coverage refusal
  fc_ok=1
  if ! $GENPY $GEN --window $W --quantile p90 --rho $RHO --cold-start-s $L \
        --out "$OUT/${W}_fc.sched.json" > "$OUT/${W}_gen.log" 2>&1; then
    if grep -q "$NO_COVERAGE $W" "$OUT/${W}_gen.log"; then
      fc_ok=0
      rm -f "$OUT/${W}_fc.sched.json"
      echo "NOTE ${W}: no forecast coverage -> fc arm skipped; hybrid degenerates to reactive"
    else
      echo "FAIL ${W}: forecast schedule generation (see ${W}_gen.log)" >&2
      return 1
    fi
  fi

  $GENPY $REGEN --window $W --mode react_point --rho $RHO --cold-start-s $L \
      --out "$OUT/${W}_re.sched.json" >> "$OUT/${W}_gen.log" 2>&1 \
    || { echo "FAIL ${W}: reactive schedule generation (see ${W}_gen.log)" >&2; return 1; }

  if [ "$fc_ok" -eq 1 ]; then
    $GENPY $COMB "$OUT/${W}_fc.sched.json" "$OUT/${W}_re.sched.json" \
        "$OUT/${W}_hybrid.sched.json" >> "$OUT/${W}_gen.log" 2>&1 \
      || { echo "FAIL ${W}: combiner (see ${W}_gen.log)" >&2; return 1; }
    tags="fc re hybrid"
  else
    $GENPY $COMB --allow-missing "$OUT/${W}_fc.sched.json" "$OUT/${W}_re.sched.json" \
        "$OUT/${W}_hybrid.sched.json" >> "$OUT/${W}_gen.log" 2>&1 \
      || { echo "FAIL ${W}: combiner fallback (see ${W}_gen.log)" >&2; return 1; }
    tags="re hybrid"
  fi

  for tag in $tags; do
    $GENPY $CONV --out "$OUT/${W}_${tag}.jsonl" --offset "$OFF" --max-requests "$MAX" \
        --encoder-workers 2 --worker-schedule "$OUT/${W}_${tag}.sched.json" \
        > "$OUT/${W}_${tag}.conv.log" 2>&1 \
      || { echo "FAIL ${W}_${tag}: replay (see ${W}_${tag}.conv.log)" >&2; return 1; }
    [ -s "$OUT/${W}_${tag}.jsonl.stats.json" ] \
      || { echo "FAIL ${W}_${tag}: replay produced no stats file" >&2; return 1; }
    echo "done ${W}_${tag}"
  done
}

declare -A PIDS
for W in $FOLDS; do run_fold "$W" & PIDS[$W]=$!; done
FAILED=""
for W in $FOLDS; do
  wait "${PIDS[$W]}" || FAILED="$FAILED $W"
done
if [ -n "$FAILED" ]; then
  echo "=== per-fold encoder 3-way FAILED for:$FAILED ===" >&2
  exit 1
fi
echo "=== per-fold encoder 3-way ($FOLDS) complete ==="

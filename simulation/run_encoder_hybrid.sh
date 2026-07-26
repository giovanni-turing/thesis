#!/bin/bash
# The missing 5.6-day encoder controller: scale on CURRENT LOAD *and* FORECAST.
# Hybrid C(t) = max( forecast p90/rho issue-time , reactive observed-point/rho ).
# Regenerates pure-forecast (fc) and pure-reactive (re) through the SAME converter
# for an apples-to-apples 3-way over the aggregate 5.60-day span. Converter-only
# (fast). rho=15, cold-start L=30 for all arms.
set -u
OUT=/home/gio/tese/simulation/results/encoder_hybrid
mkdir -p "$OUT"
# schedule gen needs pandas/numpy; converter needs the aiconfigurator EncoderCostModel.
# The dynamo venv satisfies BOTH (it imports aiconfigurator); the standalone
# aiconfigurator/.venv has no python binary (dead) -- do not use it.
GENPY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
CONVPY=$GENPY
GEN=/home/gio/tese/verification/scripts/forecast_schedule_issuetime.py
REGEN=/home/gio/tese/verification/scripts/reactive_quantile_schedule.py
CONV=/home/gio/tese/workload/trace_to_two_pool.py
COMB=/home/gio/tese/simulation/combine_schedules.py
OFFSET=250399; MAXREQ=749601; RHO=15; L=30

echo "-- forecast issue-time schedule --"
$GENPY $GEN --window aggregate --quantile p90 --rho $RHO --cold-start-s $L \
  --out "$OUT/fc.sched.json" 2>&1 | tail -2
echo "-- reactive (current observed load) schedule --"
$GENPY $REGEN --window aggregate --mode react_point --rho $RHO --cold-start-s $L \
  --out "$OUT/re.sched.json" 2>&1 | tail -2
echo "-- hybrid = max(forecast, reactive) --"
$GENPY $COMB "$OUT/fc.sched.json" "$OUT/re.sched.json" "$OUT/hybrid.sched.json"

for tag in fc re hybrid; do
  echo "-- replay $tag over aggregate 5.60d --"
  $CONVPY $CONV --out "$OUT/${tag}.jsonl" --offset $OFFSET --max-requests $MAXREQ \
    --encoder-workers 2 --worker-schedule "$OUT/${tag}.sched.json" \
    > "$OUT/${tag}.conv.log" 2>&1 && echo "   done $tag" || { echo "   FAIL $tag"; tail -5 "$OUT/${tag}.conv.log"; }
done
echo "=== encoder hybrid (aggregate 5.60d) complete ==="

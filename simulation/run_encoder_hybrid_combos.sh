#!/bin/bash
# "Which combination?" -- sweep the hybrid's forecast arm quantile {p50,p70,p90} combined via
# pointwise max with the reactive arm, on F6 (the e13 breaker). Question: since reactive is the
# safety net, can a CHEAPER forecast quantile still pass e13, giving a cost-minimal robust hybrid?
# SEQUENTIAL (one replay at a time) + RSS-watched -- encoder converter only (~hundreds of MB), no
# dynamo.replay. rho=15/L=30, react_point/p90 reactive arm (fixed for comparability).
set -u
OUT=/home/gio/tese/simulation/results/encoder_hybrid/combos
mkdir -p "$OUT"
PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
GEN=/home/gio/tese/verification/scripts/forecast_schedule_issuetime.py
REGEN=/home/gio/tese/verification/scripts/reactive_quantile_schedule.py
CONV=/home/gio/tese/workload/trace_to_two_pool.py
COMB=/home/gio/tese/simulation/combine_schedules.py
OFF=751286; MAX=84329; RHO=15; L=30

# reactive arm (shared safety net)
$PY $REGEN --window F6 --mode react_point --rho $RHO --cold-start-s $L --out "$OUT/re.sched.json" >/dev/null 2>&1

replay(){ # tag sched
  local tag=$1 sched=$2
  $PY $CONV --out "$OUT/${tag}.jsonl" --offset $OFF --max-requests $MAX \
    --encoder-workers 2 --worker-schedule "$sched" > "$OUT/${tag}.conv.log" 2>&1 &
  local pid=$!
  local peak=0
  while kill -0 $pid 2>/dev/null; do
    r=$(ps -o rss= -p $pid 2>/dev/null || echo 0); [ "${r:-0}" -gt "$peak" ] && peak=$r; sleep 1
  done
  wait $pid; local rc=$?
  printf "  %-14s rc=%s peakRSS=%dMB\n" "$tag" "$rc" "$((peak/1024))"
}

for q in p50 p70 p90; do
  $PY $GEN --window F6 --quantile $q --rho $RHO --cold-start-s $L --out "$OUT/fc_$q.sched.json" >/dev/null 2>&1
  $PY $COMB "$OUT/fc_$q.sched.json" "$OUT/re.sched.json" "$OUT/h_$q.sched.json" >/dev/null 2>&1
  echo "-- forecast $q + hybrid max($q, re) --"
  replay "fc_$q"  "$OUT/fc_$q.sched.json"
  replay "h_$q"   "$OUT/h_$q.sched.json"
done
echo "-- reactive alone --"
replay "re" "$OUT/re.sched.json"
echo "=== combos sweep complete ==="

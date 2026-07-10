#!/bin/bash
AIC_PY=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
A=/home/gio/tese/simulation/results/aggregate44
OUT=/home/gio/tese/simulation/results/aggregate44_rho
CONV=/home/gio/tese/workload/trace_to_two_pool.py
run() {
  BASE="$1"; TAG="${BASE}_ds4"
  [ -f "$OUT/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  if [ -f "$A/$BASE.sched.json" ]; then SCHEDARG="--worker-schedule $A/$BASE.sched.json --encoder-workers 2"
  elif [ "$BASE" = "static_C16" ]; then SCHEDARG="--encoder-workers 16"
  else SCHEDARG="--encoder-workers 2"; fi
  $AIC_PY $CONV --out "$OUT/$TAG.jsonl" --offset 250399 --max-requests 749601 \
    $SCHEDARG --handoff-gbps 6.25 > "$OUT/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}
for B in fc_p90_L300 fc_p50_L30 react_L30 react_L300 static_C16 static_C2; do run "$B" & done
wait
echo "agg-ds4 done $(date -u +%H:%M:%S)" >> "$OUT/status.txt"

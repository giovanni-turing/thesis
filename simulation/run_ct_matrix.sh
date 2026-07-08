#!/bin/bash
# Phase 4.3 first C(t) matrix: forecast-driven encoder schedules on every
# forecast-covered window x {p50,p90} x rho{15,25}. Converter-only, parallel.
# Coverage rule (recorded): 1min forecasts start ~Oct 20 14:36 (8k-bin
# context), 15s forecasts start ~Oct 16 09:36; burst2/6 (Oct 15) are
# structurally unforecastable under the rolling-origin protocol.
set -u
VP=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
OUT=/home/gio/tese/simulation/results/ct_matrix
mkdir -p "$OUT"
declare -A RES=( [burst1]=1min [burst3]=15s [burst4]=15s [burst5]=15s [steady24h]=15s )
declare -A OFF=( [burst1]=843072 [burst3]=531966 [burst4]=565664 [burst5]=558386 [steady24h]=627019 )
declare -A NRQ=( [burst1]=64804 [burst3]=3093 [burst4]=25639 [burst5]=8983 [steady24h]=88260 )

for w in burst1 burst3 burst4 burst5 steady24h; do
  for q in p50 p90; do
    for rho in 15 25; do
      tag="${w}_${q}_rho${rho}"
      [ -f "$OUT/$tag.jsonl.stats.json" ] && { echo "skip $tag"; continue; }
      (
        $VP /home/gio/tese/simulation/forecast_schedule.py --window "$w" \
            --resolution "${RES[$w]}" --quantile "$q" --rho "$rho" \
            --cold-start-s 60 --hysteresis-min 3 \
            --out "$OUT/$tag.sched.json" > "$OUT/$tag.ctl.log" 2>&1 && \
        $VP /home/gio/tese/workload/trace_to_two_pool.py \
            --out "$OUT/$tag.jsonl" --offset "${OFF[$w]}" \
            --max-requests "${NRQ[$w]}" --encoder-workers 2 \
            --worker-schedule "$OUT/$tag.sched.json" \
            > "$OUT/$tag.sim.log" 2>&1 && \
        echo "done $tag" || echo "FAIL $tag"
      ) &
      while [ "$(jobs -r | wc -l)" -ge 20 ]; do wait -n; done
    done
  done
done
wait
echo "matrix complete"

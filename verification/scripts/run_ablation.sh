#!/bin/bash
# P2-1 / M1 ablation runner: reactive + trailing-window p90 + tail-aware (rho=15).
# Isolates anticipation (forecast) from headroom+conversion by giving a purely
# reactive controller the p90 headroom the forecast gets, sourced from PAST
# observation. Three signal types per (window,lead), encoder pool, 25 Gbps
# default handoff (matches ct_matrix + aggregate44 references), rho=15, hyst 3min.
#   forecast p90        (reference a; existing forecast_schedule.py)
#   react_point         (reference b; thesis reactive baseline)
#   react_quantile p90  (THE ABLATION; W in {120,240,480}s trailing window)
set -u
EDA=/home/gio/tese/eda/.venv/bin/python
AIC=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
FS=/home/gio/tese/simulation/forecast_schedule.py
RQ=/home/gio/tese/verification/scripts/reactive_quantile_schedule.py
CONV=/home/gio/tese/workload/trace_to_two_pool.py
PARQ=/home/gio/tese/predictors/results/chronos_images.parquet
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json
O=/home/gio/tese/simulation/results/rerun_verify
mkdir -p "$O"

# window -> offset max_requests resolution
declare -A OFF=( [burst3]=531966 [burst1]=843072 [aggregate]=250399 )
declare -A NRQ=( [burst3]=3093   [burst1]=64804  [aggregate]=749601 )
declare -A RES=( [burst3]=15s    [burst1]=1min   [aggregate]=15s )

conv() {  # tag  window  sched.json
  local TAG=$1 W=$2 SCH=$3
  [ -f "$O/$TAG.jsonl.stats.json" ] && { echo "skip $TAG"; return; }
  $AIC $CONV --out "$O/$TAG.jsonl" --offset "${OFF[$W]}" --max-requests "${NRQ[$W]}" \
    --encoder-workers 2 --worker-schedule "$SCH" > "$O/$TAG.sim.log" 2>&1 \
    && { rm -f "$O/$TAG.jsonl"; echo "done $TAG"; } || echo "FAIL $TAG (see $O/$TAG.sim.log)"
}

gen_forecast() { # window lead
  local W=$1 L=$2 TAG="fc_p90_${W}_L${L}"
  $EDA $FS --window "$W" --policy forecast --resolution "${RES[$W]}" --quantile p90 \
    --rho 15 --cold-start-s "$L" --hysteresis-min 3 --parquet "$PARQ" \
    --out "$O/$TAG.sched.json" > "$O/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return 1; }
  echo "$TAG $W"
}
gen_reactpoint() { # window lead
  local W=$1 L=$2 TAG="react_point_${W}_L${L}"
  $EDA $RQ --window "$W" --mode react_point --resolution "${RES[$W]}" --rho 15 \
    --cold-start-s "$L" --hysteresis-min 3 --out "$O/$TAG.sched.json" \
    > "$O/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return 1; }
  echo "$TAG $W"
}
gen_reactq() { # window lead windowsec
  local W=$1 L=$2 RW=$3 TAG="react_p90_W${RW}_${W}_L${L}"
  $EDA $RQ --window "$W" --mode react_quantile --quantile p90 --react-window-s "$RW" \
    --resolution "${RES[$W]}" --rho 15 --cold-start-s "$L" --hysteresis-min 3 \
    --out "$O/$TAG.sched.json" > "$O/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return 1; }
  echo "$TAG $W"
}

# ---------- bursts: all three signal types, both leads (cap concurrency) ----------
CAP=6
for W in burst3 burst1; do
  for L in 30 300; do
    ( gen_forecast   "$W" "$L" && conv "fc_p90_${W}_L${L}"      "$W" "$O/fc_p90_${W}_L${L}.sched.json" ) &
    while [ "$(jobs -r | wc -l)" -ge $CAP ]; do wait -n; done
    ( gen_reactpoint "$W" "$L" && conv "react_point_${W}_L${L}" "$W" "$O/react_point_${W}_L${L}.sched.json" ) &
    while [ "$(jobs -r | wc -l)" -ge $CAP ]; do wait -n; done
    for RW in 120 240 480; do
      ( gen_reactq "$W" "$L" "$RW" && conv "react_p90_W${RW}_${W}_L${L}" "$W" "$O/react_p90_W${RW}_${W}_L${L}.sched.json" ) &
      while [ "$(jobs -r | wc -l)" -ge $CAP ]; do wait -n; done
    done
  done
done
wait
echo "bursts done $(date -u +%H:%M:%S)"

# ---------- aggregate: reuse existing rho15/25Gbps references, run ablation only ----------
# references already exist: simulation/results/aggregate44/{fc_p90_L30,fc_p90_L300,react_L30,react_L300}
for L in 30 300; do
  for RW in 120 240 480; do
    gen_reactq aggregate "$L" "$RW"
  done
done
# run aggregate converter cells 3-way parallel (heavy: 749601 reqs each)
for L in 30 300; do
  for RW in 120 240 480; do
    conv "react_p90_W${RW}_aggregate_L${L}" aggregate "$O/react_p90_W${RW}_aggregate_L${L}.sched.json" &
    while [ "$(jobs -r | wc -l)" -ge 3 ]; do wait -n; done
  done
done
wait
echo "aggregate done $(date -u +%H:%M:%S)"
echo "ALL DONE $(date -u +%H:%M:%S)"
